import asyncio
from typing import List, Dict, Any
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

    async def execute_extract(self, node, page):
        """Execute an extract statement."""
        column_name = node.column_name
        selector = node.selector
        
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                self.current_row[column_name] = text
                print(f"Extracted '{column_name}': {text}")
            else:
                print(f"Warning: Selector '{selector}' not found")
                self.current_row[column_name] = None
        except Exception as e:
            print(f"Error extracting '{column_name}': {e}")
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

    async def execute_node(self, node, page):
        """Execute a single AST node."""
        if node.type == NodeType.GOTO_URL:
            await self.execute_goto_url(node, page)
        elif node.type == NodeType.EXTRACT:
            await self.execute_extract(node, page)
        elif node.type == NodeType.SAVE_ROW:
            await self.execute_save_row(node, page)
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