from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, cast
from parser import NodeType, ASTNode
from browser.interface import BrowserAutomation, Element
from browser.selector import Selector
from browser.factory import BrowserFactory
import traceback

class Interpreter:
    _current_instance = None
    
    @classmethod
    def get_current_instance(cls):
        return cls._current_instance
        
    def __init__(self, ast: ASTNode) -> None:
        """Initialize the interpreter with an AST."""
        self.ast: ASTNode = ast
        self.current_row: Dict[str, Any] = {}  # Current row bein
        self.rows: List[Dict[str, Any]] = []  # All rows collected
        
        # Store references as selectors (CSS selector strings)
        self.element_references: Dict[str, str] = {}
        # Store foreach indexes for variable selectors
        self.foreach_indexes: Dict[str, int] = {}
        
        # Browser automation
        self.browser_automation: Optional[BrowserAutomation] = None
        
        # Set as current instance
        Interpreter._current_instance = self
    
    def create_selector(self, selector_str: str) -> Selector:
        """Create a Selector object from a selector string, resolving variable references."""
        
        # Variable reference with additional selector: '@var_name .some-class'
        if ' ' in selector_str and selector_str.startswith('@'):
            parts = selector_str.split(' ', 1)
            var_name = parts[0]
            child_selector = parts[1]
                        
            if var_name in self.element_references:
                # Get the base selector for this variable
                base_selector = self.element_references[var_name]
                
                # If the base selector itself is a variable reference, resolve it first
                if base_selector.startswith('@'):
                    parent_selector = self.create_selector(base_selector)
                else:
                    parent_selector = Selector(base_selector)
                
                # Pass the index as a property of the selector
                index = self.foreach_indexes.get(var_name)
                return Selector(child_selector, parent=parent_selector, index=index)
            else:
                return Selector(selector_str)  # Fall back to regular selector
        
        # Just a variable reference: '@var_name'
        elif selector_str.startswith('@'):
            var_name = selector_str
            
            if var_name in self.element_references:
                base_selector = self.element_references[var_name]
                
                # If the base selector itself is a variable reference, resolve it recursively
                if base_selector.startswith('@'):
                    selector = self.create_selector(base_selector)
                else:
                    selector = Selector(base_selector)

                # Pass the index as a property of the selector
                index = self.foreach_indexes.get(var_name)
                if index is not None:
                    selector.index = index
                return selector
            else:
                return Selector(None)  # Empty selector
        
        # Regular CSS selector
        return Selector(selector_str)
    
    def create_selectors(self, selector_strings: List[str]) -> List[Selector]:
        """Convert a list of selector strings to Selector objects."""
        return [self.create_selector(s) for s in selector_strings]

    async def resolve_selector(self, selector: Selector) -> Optional[Element]:
        """Resolve a Selector to an Element."""
        if selector.parent is None:
            # Direct page query
            if selector.css_selector is None:
                return None
                
            # If we have an index, get all elements and select the one at the index
            if selector.index is not None:
                elements = await self.browser_automation.query_selector_all(selector.css_selector)
                if elements and 0 <= selector.index < len(elements):
                    return elements[selector.index]
                return None
            else:
                return await self.browser_automation.query_selector(selector.css_selector)
        
        # Resolve parent first
        parent_element = await self.resolve_selector(selector.parent)
        if parent_element is None:
            return None
        
        # No additional selector needed?
        if selector.css_selector is None:
            return parent_element
            
        # If we have an index, get all elements and select the one at the index
        if selector.index is not None:
            elements = await parent_element.query_all(selector.css_selector)
            if elements and 0 <= selector.index < len(elements):
                return elements[selector.index]
            return None
        else:
            # Query within parent
            return await parent_element.query(selector.css_selector)
    
    async def resolve_selectors(self, selectors: List[Selector]) -> Optional[Element]:
        """Try each selector in the list and return the first one that resolves."""
        for selector in selectors:
            element = await self.resolve_selector(selector)
            if element is not None:
                return element
        return None
    
    async def resolve_all_elements(self, selector: Selector) -> List[Element]:
        """Resolve a selector to multiple elements."""
        if selector.parent is None:
            if selector.css_selector is None:
                return []
            return await self.browser_automation.query_selector_all(selector.css_selector)
        
        parent_element = await self.resolve_selector(selector.parent)
        if parent_element is None:
            return []
            
        if selector.css_selector is None:
            return [parent_element]
            
        return await parent_element.query_all(selector.css_selector)

    async def execute_goto_url(self, node: ASTNode) -> bool:
        """Execute a goto_url statement."""
        url: str = cast(str, node.url)
        await self.browser_automation.goto(url)
        print(f"Navigated to URL: {url}")
        return True
    
    async def execute_goto_href(self, node: ASTNode) -> bool:
        """Execute a goto_href statement."""
        selectors: List[str] = cast(List[str], node.selectors)
        
        selector_objects = self.create_selectors(selectors)
        element = await self.resolve_selectors(selector_objects)
        
        if element:
            href = await self.browser_automation.extract_attribute(element, "href")
            if href:
                await self.browser_automation.goto(href)
                print(f"Navigated to href: {href}")
                return True
            else:
                print(f"Warning: No 'href' attribute found for the element")
                return False
        else:
            print(f"Warning: None of the selectors for goto_href were found")
            return False

    async def execute_extract(self, node: ASTNode) -> bool:
        """Execute an extract statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        
        selector_objects = self.create_selectors(selectors)
        element = await self.resolve_selectors(selector_objects)
        
        if element:
            text = await self.browser_automation.extract_text(element)
            self.current_row[column_name] = text
            print(f"Extracted '{column_name}': {text}")
        else:
            self.current_row[column_name] = None
            print(f"Warning: None of the selectors for '{column_name}' were found")
        
        return True

    async def execute_extract_list(self, node: ASTNode) -> bool:
        """Execute an extract_list statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        
        selector_objects = self.create_selectors(selectors)
        
        # Find all elements matching the first selector that works
        texts = []
        for selector in selector_objects:
            elements = await self.resolve_all_elements(selector)
            if elements:
                texts = [await self.browser_automation.extract_text(el) for el in elements]
                break
        
        self.current_row[column_name] = texts
        print(f"Extracted list '{column_name}' with {len(texts)} items")
        
        return True

    async def execute_extract_attribute(self, node: ASTNode) -> bool:
        """Execute an extract_attribute statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        attribute: str = cast(str, node.attribute)
        
        selector_objects = self.create_selectors(selectors)
        element = await self.resolve_selectors(selector_objects)
        
        if element:
            value = await self.browser_automation.extract_attribute(element, attribute)
            self.current_row[column_name] = value
            print(f"Extracted '{column_name}' attribute '{attribute}': {value}")
        else:
            self.current_row[column_name] = None
            print(f"Warning: None of the selectors for '{column_name}' were found")
        
        return True

    async def execute_extract_attribute_list(self, node: ASTNode) -> bool:
        """Execute an extract_attribute_list statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        attribute: str = cast(str, node.attribute)
        
        selector_objects = self.create_selectors(selectors)
        
        # Find all elements matching the first selector that works
        values = []
        for selector in selector_objects:
            elements = await self.resolve_all_elements(selector)
            if elements:
                values = [await self.browser_automation.extract_attribute(el, attribute) for el in elements]
                break
        
        self.current_row[column_name] = values
        print(f"Extracted attribute list '{column_name}.{attribute}' with {len(values)} items")
        
        return True

    async def execute_save_row(self, node: ASTNode) -> bool:
        """Execute a save_row statement."""
        # Add current row to results
        self.rows.append(self.current_row.copy())
        print(f"Saved row: {self.current_row}")
        self.current_row = {}
        return True

    async def execute_clear_row(self, node: ASTNode) -> bool:
        """Execute a clear_row statement."""
        self.current_row = {}
        print("Cleared current row")
        return True

    async def execute_set_field(self, node: ASTNode) -> bool:
        """Execute a set_field statement."""
        column_name: str = cast(str, node.column_name)
        value: str = cast(str, node.value)
        self.current_row[column_name] = value
        print(f"Set field '{column_name}' to '{value}'")
        return True

    async def execute_click(self, node: ASTNode) -> bool:
        """Execute a click statement."""
        selectors: List[str] = cast(List[str], node.selectors)
        
        selector_objects = self.create_selectors(selectors)
        element = await self.resolve_selectors(selector_objects)
        
        if element:
            success = await self.browser_automation.click(element)
            if success:
                print(f"Clicked element with one of the selectors: {selectors}")
                return True
            else:
                print(f"Warning: Click operation failed")
                return False
        else:
            print(f"Warning: None of the selectors for click were found")
            return False

    async def execute_history_back(self, node: ASTNode) -> bool:
        """Execute a history_back statement."""
        await self.browser_automation.go_back()
        print("Navigated back in history")
        return True

    async def execute_history_forward(self, node: ASTNode) -> bool:
        """Execute a history_forward statement."""
        await self.browser_automation.go_forward()
        print("Navigated forward in history")
        return True

    async def execute_log(self, node: ASTNode) -> bool:
        """Execute a log statement."""
        message: str = cast(str, node.message)
        print(f"LOG: {message}")
        return True

    async def execute_throw(self, node: ASTNode) -> bool:
        """Execute a throw statement."""
        message: str = cast(str, node.message)
        raise Exception(f"SCRIPT ERROR: {message}")

    async def execute_timestamp(self, node: ASTNode) -> bool:
        """Execute a timestamp statement."""
        column_name: str = cast(str, node.column_name)
        timestamp = datetime.now().isoformat()
        self.current_row[column_name] = timestamp
        print(f"Set timestamp '{column_name}' to '{timestamp}'")
        return True

    async def execute_exit(self, node: ASTNode) -> bool:
        """Execute an exit statement."""
        print("Exiting script execution")
        return False

    async def execute_foreach(self, node: ASTNode) -> bool:
        """Execute a foreach statement."""
        selectors: List[str] = cast(List[str], node.selectors)
        element_var_name: str = cast(str, node.element_var_name)
        loop_body: List[ASTNode] = cast(List[ASTNode], node.loop_body)
        
        # Create selector objects
        selector_objects = self.create_selectors(selectors)
        
        # Find all elements for the first working selector
        all_elements = []
        working_selector_str = None
        
        for i, selector in enumerate(selector_objects):
            elements = await self.resolve_all_elements(selector)
            if elements:
                all_elements = elements
                working_selector_str = selectors[i]
                break
        
        if not all_elements:
            print(f"Warning: No elements found for foreach selector: {selectors}")
            return True
            
        # Save the selector string for this variable
        self.element_references[element_var_name] = working_selector_str
        
        print(f"Found {len(all_elements)} elements for foreach loop with selector '{working_selector_str}'")
        
        # Process each element in the collection
        for i, element in enumerate(all_elements):
            # Set the index for this iteration
            self.foreach_indexes[element_var_name] = i
            
            try:
                # Execute each statement in the loop body for this element
                for statement in loop_body:
                    should_continue = await self.execute_node(statement)
                    if not should_continue:
                        return False
            except Exception as e:
                print(f"Error in foreach loop iteration {i}: {e}")
        
        # Remove the element reference and index after the loop
        if element_var_name in self.element_references:
            del self.element_references[element_var_name]
        if element_var_name in self.foreach_indexes:
            del self.foreach_indexes[element_var_name]
            
        return True

    async def execute_select(self, node: ASTNode) -> bool:
        """Execute a select statement."""
        selectors: List[str] = cast(List[str], node.selectors)
        var_name: str = cast(str, node.element_var_name)
        
        # Create selector objects
        selector_objects = self.create_selectors(selectors)
        
        # Find the first working selector
        working_selector_str = None
        for i, selector in enumerate(selector_objects):
            element = await self.resolve_selector(selector)
            if element:
                working_selector_str = selectors[i]
                break
        
        if working_selector_str:
            # Save the selector for this variable
            self.element_references[var_name] = working_selector_str
            print(f"Selected elements with selector '{working_selector_str}' as {var_name}")
        else:
            print(f"Warning: Failed to find elements with any of the provided selectors")
            
        return True

    async def evaluate_condition(self, node: ASTNode) -> bool:
        """Evaluate a condition node to a boolean result."""
        if node.type == NodeType.CONDITION_EXISTS:
            selectors: List[str] = cast(List[str], node.selectors)
            selector_objects = self.create_selectors(selectors)
            
            # Check if any of the selectors resolve to an element
            for selector in selector_objects:
                element = await self.resolve_selector(selector)
                if element:
                    return True
            return False
            
        elif node.type == NodeType.CONDITION_AND:
            left_result = await self.evaluate_condition(node.left)
            if not left_result:
                return False
            return await self.evaluate_condition(node.right)
            
        elif node.type == NodeType.CONDITION_OR:
            left_result = await self.evaluate_condition(node.left)
            if left_result:
                return True
            return await self.evaluate_condition(node.right)
            
        elif node.type == NodeType.CONDITION_NOT:
            result = await self.evaluate_condition(node.operand)
            return not result
            
        else:
            raise ValueError(f"Invalid condition node type: {node.type}")

    async def execute_if(self, node: ASTNode) -> bool:
        """Execute an if statement."""
        # Evaluate the condition
        condition_result = await self.evaluate_condition(node.condition)
        
        if condition_result:
            # Execute the true branch
            for statement in node.true_branch:
                should_continue = await self.execute_node(statement)
                if not should_continue:
                    return False
        elif node.else_if_branches:
            # Try each else-if branch
            executed_branch = False
            for condition, statements in node.else_if_branches:
                else_if_result = await self.evaluate_condition(condition)
                if else_if_result:
                    executed_branch = True
                    for statement in statements:
                        should_continue = await self.execute_node(statement)
                        if not should_continue:
                            return False
                    break
            
            # If no else-if branch executed and there's an else branch, execute it
            if not executed_branch and node.false_branch:
                for statement in node.false_branch:
                    should_continue = await self.execute_node(statement)
                    if not should_continue:
                        return False
        elif node.false_branch:
            # Execute the false branch
            for statement in node.false_branch:
                should_continue = await self.execute_node(statement)
                if not should_continue:
                    return False
        
        return True

    async def execute_while(self, node: ASTNode) -> bool:
        """Execute a while statement."""
        loop_body: List[ASTNode] = cast(List[ASTNode], node.loop_body)
        
        # Loop as long as the condition is true
        iteration = 0
        max_iterations = 1000  # Safety limit to prevent infinite loops
        
        while await self.evaluate_condition(node.condition):
            iteration += 1
            if iteration > max_iterations:
                print(f"Warning: Maximum iterations ({max_iterations}) reached in while loop")
                break
                
            for statement in loop_body:
                should_continue = await self.execute_node(statement)
                if not should_continue:
                    return False
        
        return True

    async def execute_node(self, node: ASTNode) -> bool:
        """Execute a single AST node and return whether execution should continue."""
        try:
            if node.type == NodeType.PROGRAM:
                return await self.execute_program(node)
            elif node.type == NodeType.GOTO_URL:
                return await self.execute_goto_url(node)
            elif node.type == NodeType.GOTO_HREF:
                return await self.execute_goto_href(node)
            elif node.type == NodeType.EXTRACT:
                return await self.execute_extract(node)
            elif node.type == NodeType.EXTRACT_LIST:
                return await self.execute_extract_list(node)
            elif node.type == NodeType.EXTRACT_ATTRIBUTE:
                return await self.execute_extract_attribute(node)
            elif node.type == NodeType.EXTRACT_ATTRIBUTE_LIST:
                return await self.execute_extract_attribute_list(node)
            elif node.type == NodeType.SAVE_ROW:
                return await self.execute_save_row(node)
            elif node.type == NodeType.CLEAR_ROW:
                return await self.execute_clear_row(node)
            elif node.type == NodeType.SET_FIELD:
                return await self.execute_set_field(node)
            elif node.type == NodeType.CLICK:
                return await self.execute_click(node)
            elif node.type == NodeType.HISTORY_BACK:
                return await self.execute_history_back(node)
            elif node.type == NodeType.HISTORY_FORWARD:
                return await self.execute_history_forward(node)
            elif node.type == NodeType.LOG:
                return await self.execute_log(node)
            elif node.type == NodeType.THROW:
                return await self.execute_throw(node)
            elif node.type == NodeType.TIMESTAMP:
                return await self.execute_timestamp(node)
            elif node.type == NodeType.EXIT:
                return await self.execute_exit(node)
            elif node.type == NodeType.IF:
                return await self.execute_if(node)
            elif node.type == NodeType.FOREACH:
                return await self.execute_foreach(node)
            elif node.type == NodeType.WHILE:
                return await self.execute_while(node)
            elif node.type == NodeType.SELECT:
                return await self.execute_select(node)
            else:
                print(f"Warning: Unsupported node type {node.type}")
                return True
        except Exception as e:
            print(f"Error executing node {node.type} at line {node.line}: {e}")
            traceback.print_exc()
            raise

    async def execute_program(self, program: ASTNode) -> bool:
        """Execute a program (block of statements)."""
        if program.type != NodeType.PROGRAM:
            raise ValueError("Expected program node")
        
        for node in program.children:
            should_continue = await self.execute_node(node)
            if not should_continue:
                return False
        
        return True

    async def execute(self, browser_impl: str = "playwright", headless: bool = False) -> List[Dict[str, Any]]:
        """Execute the AST and return the collected rows."""
        try:
            # Create and initialize the browser automation
            self.browser_automation = BrowserFactory.create(browser_impl)
            await self.browser_automation.launch(headless=headless)
            
            # Execute the program
            await self.execute_program(self.ast)
            
            return self.rows
        except Exception as e:
            print(f"Error executing script: {e}")
            traceback.print_exc()
            return self.rows
        finally:
            if self.browser_automation:
                await self.browser_automation.cleanup()