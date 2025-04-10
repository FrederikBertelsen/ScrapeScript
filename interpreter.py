from datetime import datetime
from typing import List, Dict, Any, cast, Optional
from parser import NodeType, ASTNode
from browser.interface import BrowserAutomation, Element
from browser.selector import Selector
from browser.factory import BrowserFactory
import traceback

class Interpreter:
    """
    Executes parsed web scraping scripts by translating AST nodes into browser automation commands.
    
    Manages the scraping state, including collected data, element references, and browser context.
    """
    _current_instance = None

    @classmethod
    def get_current_instance(cls):
        """Return the current active interpreter instance."""
        return cls._current_instance

    def __init__(self, ast: ASTNode, verbose: bool = False) -> None:
        """
        Initialize the interpreter with an abstract syntax tree.
        
        Args:
            ast: Root node of the parsed script
            verbose: Whether to output detailed execution logs
        """
        self.ast: ASTNode = ast
        self.verbose: bool = verbose

        self.current_row: Dict[str, Any] = {}  # Current data row being assembled
        self.rows: List[Dict[str, Any]] = []  # Collected data rows

        # Map of variable names to their CSS selector strings
        self.element_references: Dict[str, str] = {}
        # Track current index for each foreach loop variable
        self.foreach_indexes: Dict[str, int] = {}
        
        # Stack to track row state at different loop nesting levels
        self.row_state_stack: List[Dict[str, Any]] = []

        # Browser automation interface (initialized during execution)
        self.browser_automation: Optional[BrowserAutomation] = None

        # Register as current instance
        Interpreter._current_instance = self

    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[Interpreter] {message}")

    def create_selector(self, selector_str: str) -> Selector:
        """
        Create a Selector object from a selector string, resolving variable references.
        
        Handles three patterns:
        - '@var_name .child-selector': Variable reference + descendant selector
        - '@var_name': Direct variable reference
        - 'regular > css > selector': Standard CSS selector
        
        Returns:
            A resolved Selector object
        """
        # Variable reference with additional selector: '@var_name .some-class'
        if ' ' in selector_str and selector_str.startswith('@'):
            # Split at first space
            var_name, child_selector = selector_str.split(' ', 1)
            
            # Look up the variable reference
            if var_name not in self.element_references:
                raise ValueError(f"Unknown element reference: {var_name}")
            
            # Get the actual CSS selector that the reference points to
            parent_css = self.element_references[var_name]
            
            # Create a parent selector using the actual CSS value
            parent_selector = Selector(parent_css)
            
            # If this is a foreach variable, apply the current index
            if var_name in self.foreach_indexes:
                parent_selector.index = self.foreach_indexes[var_name]
            
            # Create a child selector with the parent
            return Selector(child_selector, parent=parent_selector)
            
        elif selector_str.startswith('@'):
            # Direct variable reference
            var_name = selector_str
            
            if var_name not in self.element_references:
                raise ValueError(f"Unknown element reference: {var_name}")
            
            # Get the actual CSS selector value, not the reference name
            css_selector = self.element_references[var_name]
            selector = Selector(css_selector)
            
            # If this is a foreach variable, apply the current index
            if var_name in self.foreach_indexes:
                selector.index = self.foreach_indexes[var_name]
                
            return selector

        # Regular CSS selector
        return Selector(selector_str)

    def create_selectors(self, selector_strings: List[str]) -> List[Selector]:
        """Convert a list of selector strings to Selector objects."""
        return [self.create_selector(s) for s in selector_strings]

    async def resolve_selector(self, selector: Selector) -> Optional[Element]:
        """
        Resolve a Selector to an actual page Element.
        
        Handles nested selectors (with parents) and indexed elements.
        
        Returns:
            The matched Element or None if not found
        """
        if selector.parent is None:
            # Direct page query
            if selector.css_selector is None:
                return None

            # If we have an index, get all elements and select the one at the index
            if selector.index is not None:
                elements = await self.browser_automation.query_selector_all(selector.css_selector)
                if elements and 0 <= selector.index < len(elements):
                    return elements[selector.index]
                self._log(f"Error: Index {selector.index} out of range for selector '{selector.css_selector}' (found {len(elements) if elements else 0} elements)")
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
            self._log(f"Error: Index {selector.index} out of range for child selector '{selector.css_selector}' (found {len(elements) if elements else 0} elements)")
            return None
        else:
            # Query within parent
            return await parent_element.query(selector.css_selector)

    async def resolve_selectors(self, selectors: List[Selector]) -> Optional[Element]:
        """
        Try each selector in the list and return the first one that resolves to an element.
        
        Returns:
            The first matched Element or None if none match
        """
        for selector in selectors:
            element = await self.resolve_selector(selector)
            if element is not None:
                return element
        return None

    async def resolve_all_elements(self, selector: Selector) -> List[Element]:
        """
        Resolve a selector to multiple elements.
        
        For parent selectors, properly queries through the DOM hierarchy.
        
        Returns:
            List of matched Elements (empty list if none found)
        """
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
        """
        Navigate to the specified URL.
        
        Returns:
            True to continue script execution
        """
        url: str = cast(str, node.url)
        await self.browser_automation.goto(url)
        self._log(f"Navigated to: {url}")
        return True

    async def execute_goto_href(self, node: ASTNode) -> bool:
        """
        Navigate to the URL found in the href attribute of a matched element.
        
        Returns:
            True to continue script execution, False if navigation failed
        """
        selectors: List[str] = cast(List[str], node.selectors)
        selector_objects = self.create_selectors(selectors)
        element = await self.resolve_selectors(selector_objects)

        if element:
            href = (await self.browser_automation.extract_attribute(element, "href")).strip()
            if href:
                await self.browser_automation.goto(href)
                self._log(f"Followed link: {href}")
                return True
            else:
                self._log(f"Error: No 'href' attribute found in matched element")
                return False
        else:
            self._log(f"Error: No element found matching selectors: {selectors}")
            return False

    async def execute_extract(self, node: ASTNode) -> bool:
        """
        Extract text content from a matched element and store it in the current row.
        
        Returns:
            True to continue script execution
        """
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        selector_objects = self.create_selectors(selectors)
        element = await self.resolve_selectors(selector_objects)

        if element:
            text = (await self.browser_automation.extract_text(element)).strip()
            self.current_row[column_name] = text
            self._log(f"Extracted '{column_name}': '{text[:50]}{'...' if len(text) > 50 else ''}'")
        else:
            self.current_row[column_name] = None
            self._log(f"Warning: No element found for '{column_name}' using selectors: {selectors}")

        return True

    async def execute_extract_list(self, node: ASTNode) -> bool:
        """
        Extract text from multiple elements and store as a list in the current row.
        
        Returns:
            True to continue script execution
        """
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        selector_objects = self.create_selectors(selectors)

        # Find all elements matching the first selector that works
        texts = []
        working_selector = None
        
        for i, selector in enumerate(selector_objects):
            elements = await self.resolve_all_elements(selector)
            if elements:
                texts = [(await self.browser_automation.extract_text(el)).strip() for el in elements]
                working_selector = selectors[i]
                break

        self.current_row[column_name] = texts
        if texts:
            self._log(f"Extracted list '{column_name}' with {len(texts)} items using '{working_selector}'")
        else:
            self._log(f"Warning: No elements found for list '{column_name}' using any selectors")

        return True

    async def execute_extract_attribute(self, node: ASTNode) -> bool:
        """
        Extract an attribute from a matched element and store it in the current row.
        
        Returns:
            True to continue script execution
        """
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        attribute: str = cast(str, node.attribute)
        selector_objects = self.create_selectors(selectors)
        element = await self.resolve_selectors(selector_objects)

        if element:
            value = (await self.browser_automation.extract_attribute(element, attribute)).strip()
            self.current_row[column_name] = value
            self._log(f"Extracted '{column_name}' attribute '{attribute}': '{value[:50]}{'...' if len(value) > 50 else ''}'")
        else:
            self.current_row[column_name] = None
            self._log(f"Warning: No element found for attribute '{attribute}' using selectors: {selectors}")

        return True

    async def execute_extract_attribute_list(self, node: ASTNode) -> bool:
        """
        Extract an attribute from multiple elements and store as a list in the current row.
        
        Returns:
            True to continue script execution
        """
        column_name: str = cast(str, node.column_name)
        selectors: List[str] = cast(List[str], node.selectors)
        attribute: str = cast(str, node.attribute)
        selector_objects = self.create_selectors(selectors)

        # Find all elements matching the first selector that works
        values = []
        working_selector = None
        
        for i, selector in enumerate(selector_objects):
            elements = await self.resolve_all_elements(selector)
            if elements:
                values = [(await self.browser_automation.extract_attribute(el, attribute)).strip() for el in elements]
                working_selector = selectors[i]
                break

        self.current_row[column_name] = values
        if values:
            self._log(f"Extracted attribute '{attribute}' list for '{column_name}' with {len(values)} items using '{working_selector}'")
        else:
            self._log(f"Warning: No elements found for attribute list '{column_name}.{attribute}' using any selectors")

        return True

    async def execute_save_row(self, node: ASTNode) -> bool:
        """
        Save the current data row to the results collection and restore it to the state
        before entering the loop (or empty if not in a loop).
        
        Returns:
            True to continue script execution
        """
        # Add current row to results
        self.rows.append(self.current_row.copy())
        col_count = len(self.current_row)
        self._log(f"Saved data row #{len(self.rows)} with {col_count} fields")
        
        # Restore row state from the most recent loop context
        if self.row_state_stack:
            # Restore to the state before entering the loop
            self.current_row = self.row_state_stack[-1].copy()
            self._log(f"Restored row state with {len(self.current_row)} fields from loop context")
        else:
            # Not in a loop, clear the row
            self.current_row = {}
            self._log("No loop context found, cleared current row")
            
        return True

    async def execute_clear_row(self, node: ASTNode) -> bool:
        """
        Clear the current data row without saving it.
        
        Returns:
            True to continue script execution
        """
        field_count = len(self.current_row)
        self.current_row = {}
        self._log(f"Cleared current row ({field_count} fields discarded)")
        return True

    async def execute_set_field(self, node: ASTNode) -> bool:
        """
        Set a field in the current row to a static value.
        
        Returns:
            True to continue script execution
        """
        column_name: str = cast(str, node.column_name)
        value: str = cast(str, node.value)
        self.current_row[column_name] = value
        self._log(f"Set field '{column_name}' = '{value}'")
        return True

    async def execute_click(self, node: ASTNode) -> bool:
        """
        Click on an element matched by selectors.
        
        Returns:
            True to continue script execution, False if click failed
        """
        selectors: List[str] = cast(List[str], node.selectors)
        selector_objects = self.create_selectors(selectors)
        element = await self.resolve_selectors(selector_objects)

        if element:
            success = await self.browser_automation.click(element)
            if success:
                self._log(f"Clicked element successfully")
                return True
            else:
                self._log(f"Error: Click operation failed (element might be blocked or not clickable)")
                return False
        else:
            self._log(f"Error: No clickable element found matching selectors: {selectors}")
            return False

    async def execute_history_back(self, node: ASTNode) -> bool:
        """
        Navigate back in browser history.
        
        Returns:
            True to continue script execution
        """
        await self.browser_automation.go_back()
        self._log("Navigated back in history")
        return True

    async def execute_history_forward(self, node: ASTNode) -> bool:
        """
        Navigate forward in browser history.
        
        Returns:
            True to continue script execution
        """
        await self.browser_automation.go_forward()
        self._log("Navigated forward in history")
        return True

    async def execute_log(self, node: ASTNode) -> bool:
        """
        Output a user-defined log message.
        
        Returns:
            True to continue script execution
        """
        message: str = cast(str, node.message)
        print(f"[Script Log] {message}")  # Always show user logs regardless of verbose setting
        return True

    async def execute_throw(self, node: ASTNode) -> bool:
        """
        Raise an exception with a user-defined message.
        
        Raises:
            Exception: Always raised with the provided message
        """
        message: str = cast(str, node.message)
        raise Exception(f"Script error: {message}")

    async def execute_timestamp(self, node: ASTNode) -> bool:
        """
        Store current timestamp in the specified field.
        
        Returns:
            True to continue script execution
        """
        column_name: str = cast(str, node.column_name)
        timestamp = datetime.now().isoformat()
        self.current_row[column_name] = timestamp
        self._log(f"Added timestamp to '{column_name}': {timestamp}")
        return True

    async def execute_exit(self, node: ASTNode) -> bool:
        """
        Exit script execution cleanly.
        
        Returns:
            False to stop script execution
        """
        self._log("Exiting script execution (exit command)")
        return False

    async def execute_foreach(self, node: ASTNode) -> bool:
        """
        Execute a foreach loop over elements matching the specified selector.

        Creates a variable reference that can be used in nested operations
        to refer to the current element in the iteration.
        """
        selectors: List[str] = cast(List[str], node.selectors)
        element_var_name: str = cast(str, node.element_var_name)
        loop_body: List[ASTNode] = cast(List[ASTNode], node.loop_body)

        # Create selector objects from selector strings
        selector_objects = self.create_selectors(selectors)

        # Find first working selector and get matching elements
        all_elements = []
        working_selector = None
        working_selector_str = None

        for i, selector in enumerate(selector_objects):
            try:
                elements = await self.resolve_all_elements(selector)
                if elements:
                    all_elements = elements
                    working_selector = selector
                    working_selector_str = selectors[i]
                    break
            except Exception as e:
                self._log(f"Error resolving selector '{selectors[i]}': {str(e)}")
                continue

        if not all_elements:
            self._log(f"No elements found for foreach loop with selectors: {selectors}")
            return True  # Continue execution despite no elements found

        # Store the CSS selector for variable references within the loop
        # Important: Store the actual CSS selector, not the reference with @
        if working_selector and working_selector.css_selector:
            actual_css = working_selector.css_selector
            self.element_references[element_var_name] = actual_css
        else:
            # Fallback to the original selector string (this won't work if it has @references)
            self.element_references[element_var_name] = working_selector_str

        self._log(f"Iterating through {len(all_elements)} elements using selector '{working_selector_str}'")
        
        # Save current row state before entering the loop
        self.row_state_stack.append(self.current_row.copy())
        self._log(f"Saved row state with {len(self.current_row)} fields before entering foreach loop")

        try:
            # Process each element in the collection
            for i, element in enumerate(all_elements):
                # Set the current iteration index
                self.foreach_indexes[element_var_name] = i
                
                try:
                    # Execute each statement in the loop body
                    for statement in loop_body:
                        should_continue = await self.execute_node(statement)
                        if not should_continue:
                            return False
                except Exception as e:
                    self._log(f"Error in foreach iteration {i}/{len(all_elements)}: {str(e)}")
                    raise  # Re-raise to maintain error propagation
        finally:
            # Clean up variable references after loop completion
            if element_var_name in self.element_references:
                del self.element_references[element_var_name]
            if element_var_name in self.foreach_indexes:
                del self.foreach_indexes[element_var_name]
                
            # Remove the row state for this loop
            if self.row_state_stack:
                self.row_state_stack.pop()
                self._log("Restored previous row state context after foreach loop")

        return True

    async def execute_select(self, node: ASTNode) -> bool:
        """
        Select elements using provided selectors and store as a named reference.
        
        Creates a variable that can be referenced in subsequent operations.
        """
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
            # Store selector for future references
            self.element_references[var_name] = working_selector_str
            self._log(f"Created reference '{var_name}' using selector '{working_selector_str}'")
        else:
            self._log(f"Failed to create reference '{var_name}': no matching elements found")

        return True

    async def evaluate_condition(self, node: ASTNode) -> bool:
        """
        Evaluate a conditional expression and return the boolean result.
        
        Handles EXISTS, AND, OR, and NOT condition types.
        """
        if node.type == NodeType.CONDITION_EXISTS:
            selectors: List[str] = cast(List[str], node.selectors)
            selector_objects = self.create_selectors(selectors)

            # Check if any selector resolves to an element
            for selector in selector_objects:
                element = await self.resolve_selector(selector)
                if element:
                    return True
            return False

        elif node.type == NodeType.CONDITION_AND:
            # Short-circuit evaluation for AND
            left_result = await self.evaluate_condition(node.left)
            if not left_result:
                return False
            return await self.evaluate_condition(node.right)

        elif node.type == NodeType.CONDITION_OR:
            # Short-circuit evaluation for OR
            left_result = await self.evaluate_condition(node.left)
            if left_result:
                return True
            return await self.evaluate_condition(node.right)

        elif node.type == NodeType.CONDITION_NOT:
            # Negate the evaluation of the operand
            result = await self.evaluate_condition(node.operand)
            return not result

        else:
            raise ValueError(f"Unsupported condition type: {node.type}")

    async def execute_if(self, node: ASTNode) -> bool:
        """
        Execute conditional branching logic.
        
        Evaluates a condition and executes appropriate branch (if/else-if/else).
        """
        # Evaluate the condition
        condition_result = await self.evaluate_condition(node.condition)

        if condition_result:
            # Execute the if branch
            self._log("Condition evaluated to true, executing if branch")
            for statement in node.true_branch:
                should_continue = await self.execute_node(statement)
                if not should_continue:
                    return False
        elif node.else_if_branches:
            # Try each else-if branch
            executed_branch = False
            
            for i, (condition, statements) in enumerate(node.else_if_branches):
                else_if_result = await self.evaluate_condition(condition)
                if else_if_result:
                    executed_branch = True
                    self._log(f"Else-if condition #{i+1} evaluated to true, executing branch")
                    for statement in statements:
                        should_continue = await self.execute_node(statement)
                        if not should_continue:
                            return False
                    break

            # If no else-if branch executed and there's an else branch, execute it
            if not executed_branch and node.false_branch:
                self._log("All conditions evaluated to false, executing else branch")
                for statement in node.false_branch:
                    should_continue = await self.execute_node(statement)
                    if not should_continue:
                        return False
        elif node.false_branch:
            # Execute the else branch
            self._log("Condition evaluated to false, executing else branch")
            for statement in node.false_branch:
                should_continue = await self.execute_node(statement)
                if not should_continue:
                    return False

        return True

    async def execute_while(self, node: ASTNode) -> bool:
        """
        Execute a while loop that continues as long as a condition evaluates to true.
        
        Includes safety limit to prevent infinite loops.
        """
        loop_body: List[ASTNode] = cast(List[ASTNode], node.loop_body)

        # Save current row state before entering the loop
        self.row_state_stack.append(self.current_row.copy())
        self._log(f"Saved row state with {len(self.current_row)} fields before entering while loop")

        try:
            # Loop as long as the condition is true
            iteration = 0
            max_iterations = 1000  # Safety limit to prevent infinite loops

            while await self.evaluate_condition(node.condition):
                iteration += 1
                if iteration > max_iterations:
                    self._log(f"Loop safety limit reached ({max_iterations} iterations) - terminating while loop")
                    break

                self._log(f"While loop iteration {iteration}")
                for statement in loop_body:
                    should_continue = await self.execute_node(statement)
                    if not should_continue:
                        return False
        finally:
            # Remove the row state for this loop
            if self.row_state_stack:
                self.row_state_stack.pop()
                self._log("Restored previous row state context after while loop")

        return True

    async def execute_node(self, node: ASTNode) -> bool:
        """
        Execute a single AST node based on its type.
        
        Returns whether execution should continue (False terminates script).
        """
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
                self._log(f"Unknown node type: {node.type}")
                return True
        except Exception as e:
            print(f"Error at line {node.line}: {str(e)}")
            print(f"Node type: {node.type}")
            traceback.print_exc()
            raise

    async def execute_program(self, program: ASTNode) -> bool:
        """
        Execute the entire program by sequentially executing each statement.
        
        Returns False if execution should terminate early.
        """
        if program.type != NodeType.PROGRAM:
            raise ValueError("Expected program node but received different node type")

        for node in program.children:
            should_continue = await self.execute_node(node)
            if not should_continue:
                return False

        return True

    async def execute(self, browser_impl: str = "playwright", headless: bool = False) -> List[Dict[str, Any]]:
        """
        Main entry point for script execution.
        
        Initializes browser automation, executes the program, and returns collected results.
        
        Args:
            browser_impl: Browser implementation to use ('playwright' or other supported types)
            headless: Whether to run the browser in headless mode
        
        Returns:
            List of data rows collected during execution
        """
        try:
            # Initialize browser automation
            self.browser_automation = BrowserFactory.create(browser_impl)
            await self.browser_automation.launch(headless=headless)
            self._log(f"Browser automation launched ({browser_impl}, headless={headless})")

            # Execute the program
            await self.execute_program(self.ast)
            self._log(f"Script execution complete - collected {len(self.rows)} data rows")

            return self.rows
        except Exception as e:
            print(f"Script execution failed: {str(e)}")
            traceback.print_exc()
            return self.rows  # Return any collected rows before the error
        finally:
            if self.browser_automation:
                await self.browser_automation.cleanup()
                self._log("Browser resources cleaned up")