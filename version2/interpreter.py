import asyncio
from typing import List, Dict, Any, Tuple, Optional
from playwright.async_api import async_playwright
from parser import NodeType, ASTNode

class Interpreter:
    def __init__(self, ast):
        self.ast = ast
        self.current_row = {}  # Current row being built
        self.rows = []  # All rows collected

    async def execute_goto_url(self, node, page):
        """Execute a goto_url statement."""
        url = node.url
        await page.goto(url)
        print(f"Navigated to: {url}")

    async def try_selectors(self, selectors, page):
        """Try multiple selectors until one works, returning the first successful element or None."""
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    return element, selector
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
        return None, None

    async def execute_extract(self, node, page):
        """Execute an extract statement with multiple selector options."""
        column_name = node.column_name
        selectors = node.selectors
        
        element, used_selector = await self.try_selectors(selectors, page)
        
        if element:
            try:
                text = await element.inner_text()
                self.current_row[column_name] = text
                print(f"Extracted '{column_name}' using selector '{used_selector}': {text}")
            except Exception as e:
                print(f"Error extracting text from '{used_selector}': {e}")
                self.current_row[column_name] = None
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = None

    async def execute_extract_attribute(self, node, page):
        """Execute an extract_attribute statement with multiple selector options."""
        column_name = node.column_name
        selectors = node.selectors
        
        element, used_selector = await self.try_selectors(selectors, page)
        
        if element:
            try:
                attribute_text = await element.get_attribute(node.attribute)
                self.current_row[column_name] = attribute_text
                print(f"Extracted '{column_name}' using selector '{used_selector}' with attribute '{node.attribute}': {attribute_text}")
            except Exception as e:
                print(f"Error extracting attribute '{node.attribute}' from '{used_selector}': {e}")
                self.current_row[column_name] = None
        else:
            print(f"Warning: None of the selectors for '{column_name}' were found")
            self.current_row[column_name] = None

    async def execute_save_row(self, node, page):
        """Execute a save_row statement."""
        if self.current_row:
            self.rows.append(self.current_row.copy())  # Save a copy of the current row
            print(f"Saved row: {self.current_row}")
            self.current_row = {}  # Reset the current row
        else:
            print("Warning: Saving empty row")
            self.rows.append({})

    async def evaluate_condition_exists(self, node, page):
        """Evaluate an exists condition with multiple selector options."""
        selectors = node.selectors
        element, used_selector = await self.try_selectors(selectors, page)
        exists = element is not None
        
        if exists:
            print(f"Found element using selector: '{used_selector}'")
        else:
            print(f"None of the selectors were found: {selectors}")
            
        return exists

    async def evaluate_condition_and(self, node, page):
        """Evaluate an AND condition."""
        left_result = await self.evaluate_condition(node.left, page)
        if not left_result:  # Short-circuit evaluation
            return False
        return await self.evaluate_condition(node.right, page)

    async def evaluate_condition_or(self, node, page):
        """Evaluate an OR condition."""
        left_result = await self.evaluate_condition(node.left, page)
        if left_result:  # Short-circuit evaluation
            return True
        return await self.evaluate_condition(node.right, page)

    async def evaluate_condition_not(self, node, page):
        """Evaluate a NOT condition."""
        result = await self.evaluate_condition(node.operand, page)
        return not result

    async def evaluate_condition(self, node, page):
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

    async def execute_if(self, node, page):
        """Execute an if statement with optional else_if and else clauses."""
        # Check the main condition first
        condition_result = await self.evaluate_condition(node.condition, page)
        print(f"If condition evaluated to: {condition_result}")
        
        if condition_result:
            # Execute the true branch
            for statement in node.true_branch:
                continue_execution = await self.execute_node(statement, page)
                if not continue_execution:
                    return False
        elif node.else_if_branches:
            # Try each else_if branch in order
            executed_else_if = False
            for else_if_condition, else_if_statements in node.else_if_branches:
                else_if_result = await self.evaluate_condition(else_if_condition, page)
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


    async def execute_set_field(self, node, page):
        """Execute a set_field statement."""
        column_name = node.column_name
        value = node.value
        
        self.current_row[column_name] = value
        print(f"Set field '{column_name}' to: {value}")

    async def execute_node(self, node, page):
        """Execute a single AST node."""
        if node.type == NodeType.GOTO_URL:
            await self.execute_goto_url(node, page)
        elif node.type == NodeType.EXTRACT:
            await self.execute_extract(node, page)
        elif node.type == NodeType.EXTRACT_ATTRIBUTE:
            await self.execute_extract_attribute(node, page)
        elif node.type == NodeType.SAVE_ROW:
            await self.execute_save_row(node, page)
        elif node.type == NodeType.SET_FIELD:
            await self.execute_set_field(node, page)
        elif node.type == NodeType.IF:
            return await self.execute_if(node, page)
        elif node.type == NodeType.EXIT:
            return False  # Signal to stop execution
        return True  # Continue execution

    async def execute(self) -> List[Dict[str, Any]]:
        """Execute the program AST and return the collected data."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            for node in self.ast.children:
                continue_execution = await self.execute_node(node, page)
                if not continue_execution:
                    break
                    
            await browser.close()
            
        return self.rows