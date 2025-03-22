import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, cast
from playwright.async_api import async_playwright, Page, ElementHandle, Playwright
from parser import NodeType, ASTNode

class Interpreter:
    def __init__(self, ast: ASTNode) -> None:
        self.ast: ASTNode = ast
        self.current_row: Dict[str, Any] = {}  # Current row being built
        self.rows: List[Dict[str, Any]] = []  # All rows collected

    async def execute_goto_url(self, node: ASTNode, page: Page) -> None:
        """Execute a goto_url statement."""
        url: str = cast(str, node.url)  # We know url is not None for GOTO_URL nodes
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        print(f"Navigated to: {url}")

    async def try_selectors(self, selectors: List[str], page: Page) -> Tuple[Optional[List[ElementHandle]], Optional[str]]:
        """Try multiple selectors until one works, returning a list of elements and the selector used or None."""
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    return elements, selector
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
        return None, None

    async def execute_extract(self, node: ASTNode, page: Page) -> None:
        """Execute an extract statement with multiple selector options."""
        column_name: str = cast(str, node.column_name)  # We know column_name is not None for EXTRACT nodes
        selectors: List[str] = cast(List[str], node.selectors)  # We know selectors is not None for EXTRACT nodes
        
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements:
            element = elements[0]
            try:
                text: Optional[str] = await element.inner_text()
                self.current_row[column_name] = text
                print(f"Extracted '{column_name}' using selector '{used_selector}': {text}")
            except Exception as e:
                print(f"Error extracting text from '{used_selector}': {e}")
                self.current_row[column_name] = None
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = None

    async def execute_extract_list(self, node: ASTNode, page: Page) -> None:
        """Execute an extract_list statement with multiple selector options."""
        column_name: str = cast(str, node.column_name)  # We know column_name is not None for EXTRACT nodes
        selectors: List[str] = cast(List[str], node.selectors)  # We know selectors is not None for EXTRACT nodes
        
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements:
            try:
                texts: List[str] = [await element.inner_text() for element in elements]
                self.current_row[column_name] = texts
                print(f"Extracted '{column_name}' list using selector '{used_selector}': {texts}")
            except Exception as e:
                print(f"Error extracting text from '{used_selector}': {e}")
                self.current_row[column_name] = None
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = None

    async def execute_extract_attribute(self, node: ASTNode, page: Page) -> None:
        """Execute an extract_attribute statement with multiple selector options."""
        column_name: str = cast(str, node.column_name)  # We know column_name is not None for EXTRACT_ATTRIBUTE nodes
        selectors: List[str] = cast(List[str], node.selectors)  # We know selectors is not None for EXTRACT_ATTRIBUTE nodes
        attribute: str = cast(str, node.attribute)  # We know attribute is not None for EXTRACT_ATTRIBUTE nodes
        
        elements, used_selector = await self.try_selectors(selectors, page)
        
        if elements:
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

    async def execute_extract_attribute_list(self, node: ASTNode, page: Page) -> None:
        """Execute an extract_attribute_list statement with multiple selector options."""
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        attribute: str = cast(str, node.attribute)

        elements, used_selector = await self.try_selectors(selectors, page)

        if elements:
            try:
                attribute_texts: List[str] = [await element.get_attribute(attribute) for element in elements]
                self.current_row[column_name] = attribute_texts
                print(f"Extracted '{column_name}' list using selector '{used_selector}' with attribute '{attribute}': {attribute_texts}")
            except Exception as e:
                print(f"Error extracting attribute '{attribute}' from '{used_selector}': {e}")
                self.current_row[column_name] = None

    async def execute_save_row(self, node: ASTNode, page: Page) -> None:
        """Execute a save_row statement."""
        if self.current_row:
            self.rows.append(self.current_row.copy())  # Save a copy of the current row
            print(f"Saved row: {self.current_row}")
            self.current_row = {}  # Reset the current row
        else:
            print("Warning: Saving empty row")
            self.rows.append({})

    async def execute_clear_row(self, node: ASTNode, page: Page) -> None:
        """Execute a clear_row statement."""
        self.current_row = {}
        print("Cleared current row")

    async def evaluate_condition_exists(self, node: ASTNode, page: Page) -> bool:
        """Evaluate an exists condition with multiple selector options."""
        selectors: List[str] = cast(List[str], node.selectors)  # We know selectors is not None for CONDITION_EXISTS nodes
        elements, used_selector = await self.try_selectors(selectors, page)
        element = elements[0] if elements else None 
        
        exists: bool = element is not None
        
        if exists:
            print(f"Found element using selector: '{used_selector}'")
        else:
            print(f"None of the selectors were found: {selectors}")
            
        return exists

    async def evaluate_condition_and(self, node: ASTNode, page: Page) -> bool:
        """Evaluate an AND condition."""
        left_result: bool = await self.evaluate_condition(cast(ASTNode, node.left), page)  # We know left is not None for CONDITION_AND nodes
        if not left_result:  # Short-circuit evaluation
            return False
        return await self.evaluate_condition(cast(ASTNode, node.right), page)  # We know right is not None for CONDITION_AND nodes

    async def evaluate_condition_or(self, node: ASTNode, page: Page) -> bool:
        """Evaluate an OR condition."""
        left_result: bool = await self.evaluate_condition(cast(ASTNode, node.left), page)  # We know left is not None for CONDITION_OR nodes
        if left_result:  # Short-circuit evaluation
            return True
        return await self.evaluate_condition(cast(ASTNode, node.right), page)  # We know right is not None for CONDITION_OR nodes

    async def evaluate_condition_not(self, node: ASTNode, page: Page) -> bool:
        """Evaluate a NOT condition."""
        result: bool = await self.evaluate_condition(cast(ASTNode, node.operand), page)  # We know operand is not None for CONDITION_NOT nodes
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
        condition_result: bool = await self.evaluate_condition(cast(ASTNode, node.condition), page)  # We know condition is not None for IF nodes
        print(f"If condition evaluated to: {condition_result}")
        
        if condition_result:
            # Execute the true branch
            true_branch: List[ASTNode] = cast(List[ASTNode], node.true_branch)  # We know true_branch is not None for IF nodes
            for statement in true_branch:
                continue_execution = await self.execute_node(statement, page)
                if not continue_execution:
                    return False
        elif node.else_if_branches:
            # Try each else_if branch in order
            executed_else_if = False
            for else_if_condition, else_if_statements in node.else_if_branches:
                else_if_result: bool = await self.evaluate_condition(else_if_condition, page)
                print(f"Elseif condition evaluated to: {else_if_result}")
                
                if else_if_result:
                    # Execute this else_if branch
                    executed_else_if = True
                    for statement in else_if_statements:
                        continue_execution = await self.execute_node(statement, page)
                        if not continue_execution:
                            return False
                    break  # Exit after executing the first matching else_if
            
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

    async def execute_set_field(self, node: ASTNode, page: Page) -> None:
        """Execute a set_field statement."""
        column_name: str = cast(str, node.column_name)  # We know column_name is not None for SET_FIELD nodes
        value: str = cast(str, node.value)  # We know value is not None for SET_FIELD nodes
        
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

    async def execute_click(self, node: ASTNode, page: Page) -> None:
        """Execute a click statement with multiple selector options."""
        selectors: List[str] = cast(List[str], node.selectors)
        elements, used_selector = await self.try_selectors(selectors, page)

        if elements:
            element = elements[0]
            try:
                await element.click()
                await page.wait_for_load_state("networkidle")
                print(f"Clicked element using selector: '{used_selector}'")
            except Exception as e:
                print(f"Error clicking element using selector '{used_selector}': {e}")

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
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            if self.ast.children:
                for node in self.ast.children:
                    continue_execution = await self.execute_node(node, page)
                    if not continue_execution:
                        break
                    
            await browser.close()
            
        return self.rows