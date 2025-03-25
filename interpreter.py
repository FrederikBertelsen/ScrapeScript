from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, cast
from parser import NodeType, ASTNode
from browser.interface import Page, Element, Browser, BrowserAutomation
from browser.factory import BrowserFactory

class Interpreter:
    def __init__(self, ast: ASTNode, browser_impl: str = "playwright") -> None:
        """Initialize the interpreter with an AST."""
        self.ast: ASTNode = ast
        self.current_row: Dict[str, Any] = {}  # Current row being built
        self.rows: List[Dict[str, Any]] = []  # All rows collected
        self.browser_impl = browser_impl
        
        # Store references as (selector, optional_index)
        # For select statements: (selector, None)
        # For foreach elements: (selector, index)
        self.element_references: Dict[str, Tuple[str, Optional[int]]] = {}
        
        # Browser automation
        self.browser_automation: Optional[BrowserAutomation] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    # ======================================================================
    # SELECTOR AND ELEMENT HANDLING
    # ======================================================================
    
    async def try_selectors(self, selectors: List[str], page: Page) -> Tuple[Optional[List[Element]], Optional[str]]:
        """Try multiple selectors until one works, supporting @variable references."""
        for selector in selectors:
            # Check if this is a combined selector with reference and descendant parts
            # e.g., "@container .card-grid-item-card"
            if ' ' in selector and selector.startswith('@'):
                # Split the selector into reference and descendant parts
                parts = selector.split(' ', 1)
                ref_var = parts[0]  # e.g., "@container"
                descendant = parts[1]  # e.g., ".card-grid-item-card"
                
                if ref_var in self.element_references:
                    ref_selector, idx = self.element_references[ref_var]
                    
                    if idx is not None:
                        # This is an element from a foreach loop
                        # Get the parent elements first
                        parent_elements = await page.query_selector_all(ref_selector)
                        if 0 <= idx < len(parent_elements):
                            # Get the specific parent element
                            parent_element = parent_elements[idx]
                            # Query for the descendant within this element
                            child_elements = await parent_element.query_selector_all(descendant)
                            if child_elements:
                                return child_elements, f"{ref_selector}[{idx}] {descendant}"
                        else:
                            print(f"Warning: Element index {idx} out of range for {ref_selector}")
                            continue
                    else:
                        # This is an element from a select statement
                        # Combine the reference selector with descendant part
                        combined_selector = f"{ref_selector} {descendant}"
                        try:
                            elements = await page.query_selector_all(combined_selector)
                            if elements:
                                return elements, combined_selector
                        except Exception as e:
                            print(f"Warning: Error with combined selector '{combined_selector}': {e}")
                            continue
                else:
                    print(f"Warning: Unknown element reference: {ref_var}")
                    continue
            # Handle simple element references (variables starting with @ without descendant parts)
            elif selector.startswith('@') and selector in self.element_references:
                ref_selector, idx = self.element_references[selector]
                
                if idx is not None:
                    # This is an element from a foreach loop
                    elements = await page.query_selector_all(ref_selector)
                    if 0 <= idx < len(elements):
                        return [elements[idx]], f"{ref_selector}[{idx}]"
                    else:
                        print(f"Warning: Element index {idx} out of range for {ref_selector}")
                        continue
                else:
                    # This is an element from a select statement
                    elements = await page.query_selector_all(ref_selector)
                    if elements:
                        return elements, ref_selector
                    else:
                        continue
            
            # Regular selector (non-reference)
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    return elements, selector
            except Exception as e:
                print(f"Warning: Error with selector '{selector}': {e}")
                continue
        
        print(f"Warning: None of the selectors were found: {selectors}")
        return None, None
    
    # ======================================================================
    # DATA EXTRACTION AND MANIPULATION
    # ======================================================================
    
    async def execute_extract(self, node: ASTNode, page: Page) -> None:
        """Execute an extract statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements:
            element = elements[0]
            try:
                text = await element.text_content()
                self.current_row[column_name] = text.strip() if text else text
                print(f"Extracted '{column_name}': {text}")
            except Exception as e:
                print(f"Error extracting '{column_name}': {e}")
                self.current_row[column_name] = None
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = None

    async def execute_extract_list(self, node: ASTNode, page: Page) -> None:
        """Execute an extract_list statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements:
            try:
                text_list = []
                for element in elements:
                    text = await element.text_content()
                    if text:
                        text_list.append(text.strip())
                self.current_row[column_name] = text_list
                print(f"Extracted list '{column_name}' with {len(text_list)} items")
            except Exception as e:
                print(f"Error extracting list '{column_name}': {e}")
                self.current_row[column_name] = []
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = []

    async def execute_extract_attribute(self, node: ASTNode, page: Page) -> None:
        """Execute an extract_attribute statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        attribute: str = cast(str, node.attribute)
        
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements and len(elements) > 0:
            element = elements[0]
            try:
                attr_value = await element.get_attribute(attribute)
                self.current_row[column_name] = attr_value
                print(f"Extracted attribute '{attribute}' for '{column_name}': {attr_value}")
            except Exception as e:
                print(f"Error extracting attribute '{attribute}' for '{column_name}': {e}")
                self.current_row[column_name] = None
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = None

    async def execute_extract_attribute_list(self, node: ASTNode, page: Page) -> None:
        """Execute an extract_attribute_list statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        attribute: str = cast(str, node.attribute)

        elements, used_selector = await self.try_selectors(selectors, page)

        if elements:
            try:
                attr_values = []
                for element in elements:
                    attr_value = await element.get_attribute(attribute)
                    if attr_value:
                        attr_values.append(attr_value)
                self.current_row[column_name] = attr_values
                print(f"Extracted attribute list '{attribute}' for '{column_name}' with {len(attr_values)} items")
            except Exception as e:
                print(f"Error extracting attribute list '{attribute}' for '{column_name}': {e}")
                self.current_row[column_name] = []
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = []

    async def execute_set_field(self, node: ASTNode, page: Page) -> None:
        """Execute a set_field statement."""
        column_name: str = cast(str, node.column_name)
        value: str = cast(str, node.value)
        
        self.current_row[column_name] = value
        print(f"Set field '{column_name}' to: {value}")
    
    async def execute_timestamp(self, node: ASTNode, page: Page) -> None:
        """Execute a timestamp statement."""
        column_name: str = cast(str, node.column_name)
        timestamp = datetime.now().isoformat()

        self.current_row[column_name] = timestamp
        print(f"Set field '{column_name}' to timestamp: {timestamp}")

    async def execute_save_row(self, node: ASTNode, page: Page) -> None:
        """Execute a save_row statement."""
        if self.current_row:
            self.rows.append(self.current_row.copy())
            print(f"Saved row: {self.current_row}")
            self.current_row = {}
        else:
            print("Warning: Saving empty row")
            self.rows.append({})

    async def execute_clear_row(self, node: ASTNode, page: Page) -> None:
        """Execute a clear_row statement."""
        self.current_row = {}
        print("Cleared current row")

    # ======================================================================
    # NAVIGATION AND BROWSER INTERACTION
    # ======================================================================
    
    async def execute_goto_url(self, node: ASTNode, page: Page) -> None:
        """Execute a goto_url statement."""
        url: str = cast(str, node.url)
        await page.goto(url)
        print(f"Navigated to: {url}")

    async def execute_click(self, node: ASTNode, page: Page) -> None:
        """Execute a click statement."""
        selectors: List[str] = cast(List[str], node.selectors)
        elements, used_selector = await self.try_selectors(selectors, page)

        if elements:
            element = elements[0]
            try:
                await element.click()
                print(f"Clicked on element: {used_selector}")
            except Exception as e:
                print(f"Error clicking on element: {e}")
        else:
            print(f"Warning: No elements found to click")

    async def execute_history_forward(self, node: ASTNode, page: Page) -> None:
        """Execute a history_forward statement."""
        await page.go_forward()
        print("Navigated forward in history")

    async def execute_history_back(self, node: ASTNode, page: Page) -> None:
        """Execute a history_back statement."""
        await page.go_back()
        print("Navigated back in history")

    # ======================================================================
    # UTILITY ACTIONS
    # ======================================================================

    async def execute_log(self, node: ASTNode, page: Page) -> None:
        """Execute a log statement."""
        message: str = cast(str, node.message)
        print(f"Log: {message}")

    async def execute_throw(self, node: ASTNode, page: Page) -> None:
        """Execute a throw statement."""
        message: str = cast(str, node.message)
        raise RuntimeError(f"Script error: {message}")

    async def execute_exit(self, node: ASTNode, page: Page) -> bool:
        """Execute an exit statement."""
        print("Exiting script execution")
        return False  # Signal to stop execution

    # ======================================================================
    # CONTROL FLOW EXECUTION
    # ======================================================================
    
    async def execute_if(self, node: ASTNode, page: Page) -> bool:
        """Execute an if statement with optional else_if and else clauses."""
        # Check the main condition first
        condition_result: bool = await self.evaluate_condition(cast(ASTNode, node.condition), page)
        print(f"If condition evaluated to: {condition_result}")
        
        if condition_result:
            # Execute the true branch
            true_branch: List[ASTNode] = cast(List[ASTNode], node.true_branch)
            for statement in true_branch:
                continue_execution = await self.execute_node(statement, page)
                if not continue_execution:
                    return False
        elif node.else_if_branches:
            # Try each else_if branch in order
            executed_else_if = False
            for else_if_condition, else_if_statements in node.else_if_branches:
                else_if_result = await self.evaluate_condition(else_if_condition, page)
                print(f"Else-if condition evaluated to: {else_if_result}")
                
                if else_if_result:
                    executed_else_if = True
                    for statement in else_if_statements:
                        continue_execution = await self.execute_node(statement, page)
                        if not continue_execution:
                            return False
                    break
            
            # If no else_if branch was executed and there's an else branch, execute it
            if not executed_else_if and node.false_branch:
                for statement in node.false_branch:
                    continue_execution = await self.execute_node(statement, page)
                    if not continue_execution:
                        return False
        elif node.false_branch:
            # No else_if branches or none matched, so execute the else branch if it exists
            for statement in node.false_branch:
                continue_execution = await self.execute_node(statement, page)
                if not continue_execution:
                    return False
                    
        return True  # Continue execution

    async def execute_foreach(self, node: ASTNode, page: Page) -> bool:
        """Execute a foreach statement."""
        selectors: List[str] = cast(List[str], node.selectors)
        element_var_name: str = cast(str, node.element_var_name)
        loop_body: List[ASTNode] = cast(List[ASTNode], node.loop_body)
        
        # Get all elements matching the selector
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if not elements:
            print(f"Warning: No elements found for foreach selector: {selectors}")
            return True
        
        count = len(elements)
        print(f"Found {count} elements for foreach loop with selector '{used_selector}'")
        
        # Process each element in the collection
        for i in range(count):
            try:
                # Store this element reference with its index
                self.element_references[element_var_name] = (used_selector, i)
                print(f"Processing element {i+1}/{count} in foreach loop")
                
                # Execute the loop body for this element
                for statement in loop_body:
                    continue_execution = await self.execute_node(statement, page)
                    if not continue_execution:
                        return False
            except Exception as e:
                print(f"Error in foreach loop at index {i}: {e}")
        
        # Remove the element reference after the loop
        if element_var_name in self.element_references:
            del self.element_references[element_var_name]
            
        return True

    async def execute_while(self, node: ASTNode, page: Page) -> bool:
        """Execute a while loop."""
        condition: ASTNode = cast(ASTNode, node.condition)
        loop_body: List[ASTNode] = cast(List[ASTNode], node.loop_body)
        
        iteration = 0
        max_iterations = 1000  # Safety limit
        
        while iteration < max_iterations:
            # Evaluate the condition
            condition_result = await self.evaluate_condition(condition, page)
            if not condition_result:
                break
                
            print(f"While loop iteration {iteration+1}")
            iteration += 1
            
            # Execute the loop body
            for statement in loop_body:
                continue_execution = await self.execute_node(statement, page)
                if not continue_execution:
                    return False
        
        if iteration >= max_iterations:
            print("Warning: While loop reached maximum iterations limit")
            
        return True

    async def execute_select(self, node: ASTNode, page: Page) -> None:
        """Execute a select statement."""
        selectors: List[str] = cast(List[str], node.selectors)
        var_name: str = cast(str, node.element_var_name)
        
        # Get all elements matching the selector
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements and used_selector:
            # Store the selector for later reference
            self.element_references[var_name] = (used_selector, None)
            print(f"Selected {len(elements)} elements as '{var_name}' using selector: {used_selector}")
        else:
            print(f"Warning: No elements found for selector: {selectors}")

    # ======================================================================
    # CONDITION EVALUATION
    # ======================================================================
    
    async def evaluate_condition(self, condition: ASTNode, page: Page) -> bool:
        """Evaluate a condition node."""
        if condition.type == NodeType.CONDITION_EXISTS:
            # Check if an element exists
            selectors: List[str] = cast(List[str], condition.selectors)
            elements, _ = await self.try_selectors(selectors, page)
            exists = elements is not None and len(elements) > 0
            return exists
            
        elif condition.type == NodeType.CONDITION_AND:
            # Logical AND
            left: ASTNode = cast(ASTNode, condition.left)
            right: ASTNode = cast(ASTNode, condition.right)
            left_result = await self.evaluate_condition(left, page)
            if not left_result:  # Short-circuit evaluation
                return False
            return await self.evaluate_condition(right, page)
            
        elif condition.type == NodeType.CONDITION_OR:
            # Logical OR
            left: ASTNode = cast(ASTNode, condition.left)
            right: ASTNode = cast(ASTNode, condition.right)
            left_result = await self.evaluate_condition(left, page)
            if left_result:  # Short-circuit evaluation
                return True
            return await self.evaluate_condition(right, page)
            
        elif condition.type == NodeType.CONDITION_NOT:
            # Logical NOT
            operand: ASTNode = cast(ASTNode, condition.operand)
            return not await self.evaluate_condition(operand, page)
            
        else:
            raise ValueError(f"Unknown condition type: {condition.type}")

    # ======================================================================
    # EXECUTION MAIN LOGIC
    # ======================================================================
    
    async def execute_node(self, node: ASTNode, page: Page) -> bool:
        """Execute a single AST node."""
        try:
            if node.type == NodeType.GOTO_URL:
                await self.execute_goto_url(node, page)
            elif node.type == NodeType.EXTRACT:
                await self.execute_extract(node, page)
            elif node.type == NodeType.EXTRACT_LIST:
                await self.execute_extract_list(node, page)
            elif node.type == NodeType.EXTRACT_ATTRIBUTE:
                await self.execute_extract_attribute(node, page)
            elif node.type == NodeType.EXTRACT_ATTRIBUTE_LIST:
                await self.execute_extract_attribute_list(node, page)
            elif node.type == NodeType.SAVE_ROW:
                await self.execute_save_row(node, page)
            elif node.type == NodeType.CLEAR_ROW:
                await self.execute_clear_row(node, page)
            elif node.type == NodeType.SET_FIELD:
                await self.execute_set_field(node, page)
            elif node.type == NodeType.CLICK:
                await self.execute_click(node, page)
            elif node.type == NodeType.HISTORY_BACK:
                await self.execute_history_back(node, page)
            elif node.type == NodeType.HISTORY_FORWARD:
                await self.execute_history_forward(node, page)
            elif node.type == NodeType.LOG:
                await self.execute_log(node, page)
            elif node.type == NodeType.THROW:
                await self.execute_throw(node, page)
            elif node.type == NodeType.TIMESTAMP:
                await self.execute_timestamp(node, page)
            elif node.type == NodeType.EXIT:
                return await self.execute_exit(node, page)
            elif node.type == NodeType.SELECT:
                await self.execute_select(node, page)
            elif node.type == NodeType.IF:
                return await self.execute_if(node, page)
            elif node.type == NodeType.FOREACH:
                return await self.execute_foreach(node, page)
            elif node.type == NodeType.WHILE:
                return await self.execute_while(node, page)
            else:
                print(f"Warning: Unhandled node type: {node.type}")
                
            return True  # Continue execution
        except Exception as e:
            print(f"Error executing {node.type} node: {e}")
            return True  # Continue execution despite errors

    async def execute_program(self, node: ASTNode, page: Page) -> None:
        """Execute a program node."""
        statements: List[ASTNode] = cast(List[ASTNode], node.children)
        for statement in statements:
            continue_execution = await self.execute_node(statement, page)
            if not continue_execution:
                print("Script execution terminated early")
                break

    async def execute(self) -> List[Dict[str, Any]]:
        """Execute the AST and return the collected rows."""
        browser_closed = False
        try:
            # Initialize browser automation
            self.browser_automation = BrowserFactory.create(self.browser_impl)
            self.browser = await self.browser_automation.launch(headless=True)
            self.page = await self.browser.new_page()
            
            # Execute the program
            if self.ast.type == NodeType.PROGRAM:
                await self.execute_program(self.ast, self.page)
            else:
                raise ValueError(f"Expected program node, got {self.ast.type}")
                
            return self.rows
        except Exception as e:
            print(f"Error during script execution: {e}")
            return self.rows
        finally:
            # Clean up resources in the right order
            if self.browser and not browser_closed:
                try:
                    await self.browser.close()
                    browser_closed = True
                except Exception as e:
                    print(f"Error closing browser: {e}")
            
            # Only call cleanup after browser is closed
            if self.browser_automation:
                try:
                    await self.browser_automation.cleanup()
                except Exception as e:
                    print(f"Error during cleanup: {e}")