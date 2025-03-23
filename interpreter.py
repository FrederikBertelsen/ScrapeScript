from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, cast
from playwright.async_api import async_playwright, Page, ElementHandle
from parser import NodeType, ASTNode

class Interpreter:
    def __init__(self, ast: ASTNode) -> None:
        self.ast: ASTNode = ast
        self.current_row: Dict[str, Any] = {}  # Current row being built
        self.rows: List[Dict[str, Any]] = []  # All rows collected
        
        # Store references as (selector, optional_index)
        # For select statements: (selector, None)
        # For foreach elements: (selector, index)
        self.element_references: Dict[str, Tuple[str, Optional[int]]] = {}

    async def try_selectors(self, selectors: List[str], page: Page) -> Tuple[Optional[List[ElementHandle]], Optional[str]]:
        """Try multiple selectors until one works, supporting @variable references."""
        for selector in selectors:
            try:
                # Handle @variable references in selectors
                if selector.startswith('@'):
                    parts = selector.split(' ', 1)
                    var_name = parts[0]  # The @variable part
                    
                    if var_name not in self.element_references:
                        print(f"Warning: Reference '{var_name}' not found")
                        continue
                    
                    # Get the stored selector and index
                    base_selector, index = self.element_references[var_name]
                    
                    # Get all elements matching the base selector
                    all_elements = await page.query_selector_all(base_selector)
                    
                    if not all_elements or len(all_elements) == 0:
                        print(f"Warning: No elements found with selector '{base_selector}'")
                        continue
                        
                    if index is not None:
                        # For foreach elements: get the specific element by index
                        if index >= len(all_elements):
                            print(f"Warning: Index {index} is out of range for elements with selector '{base_selector}'")
                            continue
                            
                        element = all_elements[index]
                        
                        if len(parts) > 1:
                            # Find elements within this element using additional selector
                            descendant_selector = parts[1]
                            descendants = await element.query_selector_all(descendant_selector)
                            if descendants:
                                return descendants, f"{base_selector}[{index}] {descendant_selector}"
                        else:
                            # Just return the element itself
                            return [element], f"{base_selector}[{index}]"
                    else:
                        # For select statements: use the first element
                        element = all_elements[0]
                        
                        if len(parts) > 1:
                            # Find elements within this element using additional selector
                            descendant_selector = parts[1]
                            descendants = await element.query_selector_all(descendant_selector)
                            if descendants:
                                return descendants, f"{base_selector} {descendant_selector}"
                        else:
                            # Just return the element itself
                            return [element], base_selector
                else:
                    # Regular CSS selector
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        return elements, selector
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
        
        print(f"Warning: None of the selectors were found: {selectors}")
        return None, None

    async def execute_select(self, node: ASTNode, page: Page) -> None:
        """Execute a select statement."""
        selectors: List[str] = cast(List[str], node.selectors)
        element_var_name: str = cast(str, node.element_var_name)
        
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements and element_var_name:
            # Store the selector for this element reference (no index needed)
            self.element_references[element_var_name] = (used_selector, None)
            print(f"Selected element using selector '{used_selector}' as '{element_var_name}'")
        else:
            print(f"Warning: Could not find element for selectors: {selectors}")

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
                # Store the selector and index for this element reference
                self.element_references[element_var_name] = (used_selector, i)
                print(f"Processing element as '{element_var_name}' (element {i+1}/{count})")
                
                # Execute the loop body for this element
                for statement in loop_body:
                    continue_execution = await self.execute_node(statement, page)
                    if not continue_execution:
                        return False
            except Exception as e:
                print(f"Error processing element {i+1}: {e}")
        
        # Remove the element reference after the loop
        if element_var_name in self.element_references:
            del self.element_references[element_var_name]
        
        return True

    async def execute_extract_attribute(self, node: ASTNode, page: Page) -> None:
        """Execute an extract_attribute statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        attribute: str = cast(str, node.attribute)
        
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements and len(elements) > 0:
            element = elements[0]
            try:
                attribute_text: Optional[str] = await element.get_attribute(attribute)
                self.current_row[column_name] = attribute_text
                print(f"Extracted '{column_name}' using selector '{used_selector}' with attribute '{attribute}': {attribute_text}")
            except Exception as e:
                print(f"Error extracting attribute '{attribute}' from '{used_selector}': {e}")
                self.current_row[column_name] = None
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = None

    async def execute_extract(self, node: ASTNode, page: Page) -> None:
        """Execute an extract statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements:
            element = elements[0]
            try:
                text: str = await element.text_content() or ""
                text = text.strip()
                self.current_row[column_name] = text
                print(f"Extracted '{column_name}' using selector '{used_selector}': {text}")
            except Exception as e:
                print(f"Error extracting text from '{used_selector}': {e}")
                self.current_row[column_name] = None
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = None

    async def execute_click(self, node: ASTNode, page: Page) -> None:
        """Execute a click statement."""
        selectors: List[str] = cast(List[str], node.selectors)
        elements, used_selector = await self.try_selectors(selectors, page)

        if elements:
            element = elements[0]
            try:
                await element.click()
                await page.wait_for_load_state("networkidle")
                print(f"Clicked on element: '{used_selector}'")
            except Exception as e:
                print(f"Error clicking on '{used_selector}': {e}")
        else:
            print(f"Warning: No elements found to click")

    async def evaluate_condition_exists(self, node: ASTNode, page: Page) -> bool:
        """Evaluate an exists condition."""
        selectors: List[str] = cast(List[str], node.selectors)
        elements, used_selector = await self.try_selectors(selectors, page)
        
        exists: bool = elements is not None and len(elements) > 0
        
        if exists:
            print(f"Found element using selector: '{used_selector}'")
        else:
            print(f"None of the selectors were found: {selectors}")
            
        return exists

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
                print(f"Extracted list '{column_name}' using selector '{used_selector}': {text_list[:3]}...")
            except Exception as e:
                print(f"Error extracting text list from '{used_selector}': {e}")
                self.current_row[column_name] = []
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = []

    async def execute_extract_attribute_list(self, node: ASTNode, page: Page) -> None:
        """Execute an extract_attribute_list statement."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        attribute: str = cast(str, node.attribute)

        elements, used_selector = await self.try_selectors(selectors, page)

        if elements:
            try:
                value_list = []
                for element in elements:
                    value = await element.get_attribute(attribute)
                    if value:
                        value_list.append(value)
                
                self.current_row[column_name] = value_list
                print(f"Extracted attribute list '{column_name}' using selector '{used_selector}': {value_list[:3]}...")
            except Exception as e:
                print(f"Error extracting attribute list from '{used_selector}': {e}")
                self.current_row[column_name] = []
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = []

    async def execute_goto_url(self, node: ASTNode, page: Page) -> None:
        """Execute a goto_url statement."""
        url: str = cast(str, node.url)
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        print(f"Navigated to: {url}")

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

    async def execute_set_field(self, node: ASTNode, page: Page) -> None:
        """Execute a set_field statement."""
        column_name: str = cast(str, node.column_name)
        value: str = cast(str, node.value)
        
        self.current_row[column_name] = value
        print(f"Set field '{column_name}' to: {value}")

    async def execute_log(self, node: ASTNode, page: Page) -> None:
        """Execute a log statement."""
        message: str = cast(str, node.message)
        print(f"Log: {message}")

    async def execute_timestamp(self, node: ASTNode, page: Page) -> None:
        """Execute a timestamp statement."""
        column_name: str = cast(str, node.column_name)
        timestamp = datetime.now().isoformat()

        self.current_row[column_name] = timestamp
        print(f"Set field '{column_name}' to timestamp: {timestamp}")

    async def execute_throw(self, node: ASTNode, page: Page) -> None:
        """Execute a throw statement."""
        message: str = cast(str, node.message)
        print(f"Error: {message}")

    async def execute_history_forward(self, node: ASTNode, page: Page) -> None:
        """Execute a history_forward statement."""
        await page.go_forward()
        print("Navigated forward in history")

    async def execute_history_back(self, node: ASTNode, page: Page) -> None:
        """Execute a history_back statement."""
        await page.go_back()
        print("Navigated back in history")

    async def evaluate_condition_and(self, node: ASTNode, page: Page) -> bool:
        """Evaluate an AND condition."""
        left_result: bool = await self.evaluate_condition(cast(ASTNode, node.left), page)
        if not left_result:  # Short-circuit evaluation
            return False
        return await self.evaluate_condition(cast(ASTNode, node.right), page)

    async def evaluate_condition_or(self, node: ASTNode, page: Page) -> bool:
        """Evaluate an OR condition."""
        left_result: bool = await self.evaluate_condition(cast(ASTNode, node.left), page)
        if left_result:  # Short-circuit evaluation
            return True
        return await self.evaluate_condition(cast(ASTNode, node.right), page)

    async def evaluate_condition_not(self, node: ASTNode, page: Page) -> bool:
        """Evaluate a NOT condition."""
        result: bool = await self.evaluate_condition(cast(ASTNode, node.operand), page)
        return not result

    async def evaluate_condition(self, node: ASTNode, page: Page) -> bool:
        """Evaluate a condition and return True or False."""
        if node.type == NodeType.CONDITION_EXISTS:
            return await self.evaluate_condition_exists(node, page)
        elif node.type == NodeType.CONDITION_AND:
            return await self.evaluate_condition_and(node, page)
        elif node.type == NodeType.CONDITION_OR:
            return await self.evaluate_condition_or(node, page)
        elif node.type == NodeType.CONDITION_NOT:
            return await self.evaluate_condition_not(node, page)
        else:
            raise ValueError(f"Unknown condition type: {node.type}")

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

    async def execute_while(self, node: ASTNode, page: Page) -> bool:
        """Execute a while statement."""
        loop_body: List[ASTNode] = cast(List[ASTNode], node.loop_body)
        condition: ASTNode = cast(ASTNode, node.condition)
        
        iteration_count = 0
        max_iterations = 100  # Safety limit
        
        while iteration_count < max_iterations:
            # Evaluate the condition
            condition_result: bool = await self.evaluate_condition(condition, page)
            print(f"While condition evaluated to: {condition_result}")
            
            if not condition_result:
                break
            
            # Execute the loop body
            for statement in loop_body:
                continue_execution = await self.execute_node(statement, page)
                if not continue_execution:
                    return False
            
            iteration_count += 1
            
            # Check for maximum iteration safety limit
            if iteration_count >= max_iterations:
                print(f"Warning: Maximum iteration limit ({max_iterations}) reached in while loop")
                break
        
        return True  # Continue execution after the loop
    
    async def execute_node(self, node: ASTNode, page: Page) -> bool:
        """Execute a single AST node."""
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
        elif node.type == NodeType.IF:
            return await self.execute_if(node, page)
        elif node.type == NodeType.FOREACH:
            return await self.execute_foreach(node, page)
        elif node.type == NodeType.WHILE:
            return await self.execute_while(node, page)
        elif node.type == NodeType.SELECT:
            await self.execute_select(node, page)
        elif node.type == NodeType.LOG:
            await self.execute_log(node, page)
        elif node.type == NodeType.TIMESTAMP:
            await self.execute_timestamp(node, page)
        elif node.type == NodeType.THROW:
            await self.execute_throw(node, page)
            return False  # Stop execution after throwing an error
        elif node.type == NodeType.HISTORY_FORWARD:
            await self.execute_history_forward(node, page)
        elif node.type == NodeType.HISTORY_BACK:
            await self.execute_history_back(node, page)
        elif node.type == NodeType.CLICK:
            await self.execute_click(node, page)
        elif node.type == NodeType.EXIT:
            return False  # Signal to stop execution
        return True  # Continue execution

    async def execute(self) -> List[Dict[str, Any]]:
        """Execute the program AST and return the collected data."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            if self.ast.children:
                for node in self.ast.children:
                    continue_execution = await self.execute_node(node, page)
                    if not continue_execution:
                        break
                    
            await browser.close()
            
        return self.rows