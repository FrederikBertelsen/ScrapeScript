from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Tuple, TypeVar
from lexer import TokenType, Token

class NodeType(Enum):
    # Basic operations
    GOTO_URL = auto()
    GOTO_HREF = auto()
    EXTRACT = auto()
    EXTRACT_LIST = auto()
    EXTRACT_ATTRIBUTE = auto()
    EXTRACT_ATTRIBUTE_LIST = auto()
    SAVE_ROW = auto()
    CLEAR_ROW = auto()
    SET_FIELD = auto()
    
    # Interactions
    CLICK = auto()
    HISTORY_FORWARD = auto()
    HISTORY_BACK = auto()
    
    # Utilities
    LOG = auto()
    THROW = auto()
    TIMESTAMP = auto()
    EXIT = auto()
    
    # Program structure
    PROGRAM = auto()
    SELECT = auto()
    
    # Control flow
    IF = auto()
    FOREACH = auto()
    WHILE = auto()
    
    # Conditions
    CONDITION_EXISTS = auto()
    CONDITION_AND = auto()
    CONDITION_OR = auto()
    CONDITION_NOT = auto()
    CONDITION_IS_EMPTY = auto()
    
    # Data schema
    DATA_SCHEMA = auto()
    VARIABLE_DECLARATION = auto()

# Type alias to facilitate self-referencing ASTNode
ASTNodeT = TypeVar('ASTNodeT', bound='ASTNode')

@dataclass
class ASTNode:
    type: NodeType
    line: int
    column: int
    
    # Additional fields for specific node types
    url: Optional[str] = None  # For GOTO_URL
    column_name: Optional[str] = None  # For EXTRACT and SET_FIELD
    value: Optional[str] = None  # For SET_FIELD
    message: Optional[str] = None  # For LOG and THROW
    attribute: Optional[str] = None  # For EXTRACT_ATTRIBUTE
    selector: Optional[str] = None  # For single selector nodes
    selectors: Optional[List[str]] = None  # For nodes that support multiple selectors
    
    # Control flow fields
    condition: Optional[ASTNodeT] = None  # For IF nodes
    true_branch: Optional[List[ASTNodeT]] = None  # For IF nodes
    else_if_branches: Optional[List[Tuple[ASTNodeT, List[ASTNodeT]]]] = None  # For IF nodes with else_if
    false_branch: Optional[List[ASTNodeT]] = None  # For IF nodes
    
    # Element handling fields
    element_var_name: Optional[str] = None  # For capturing elements with 'as @variable'
    loop_body: Optional[List[ASTNodeT]] = None  # For FOREACH and WHILE nodes
    
    # Logical operations fields
    left: Optional[ASTNodeT] = None  # For logical operations
    right: Optional[ASTNodeT] = None  # For logical operations
    operand: Optional[ASTNodeT] = None  # For NOT
    
    # Program structure
    children: Optional[List[ASTNodeT]] = None  # For PROGRAM

class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        """Initialize the parser with tokens from the lexer."""
        self.tokens: List[Token] = tokens
        self.pos: int = 0
        self.current_token: Optional[Token] = self.tokens[0] if tokens else None

    # ======================================================================
    # BASIC UTILITIES
    # ======================================================================

    def advance(self) -> None:
        """Move to the next token."""
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None

    def eat(self, token_type: TokenType) -> Token:
        """Consume the current token if it matches the expected type."""
        if self.current_token and self.current_token.type == token_type:
            token = self.current_token
            self.advance()
            return token
        else:
            raise SyntaxError(f"Expected {token_type} but got {self.current_token.type if self.current_token else 'None'}")

    def skip_newlines(self) -> None:
        """Skip any newline tokens."""
        while self.current_token and self.current_token.type == TokenType.NEWLINE:
            self.advance()

    # ======================================================================
    # SELECTOR AND ELEMENT HANDLING
    # ======================================================================

    def parse_selector_list(self) -> List[str]:
        """Parse a list of selectors (string literals separated by commas)."""
        selectors: List[str] = []
        
        # Parse the first selector (required)
        selector_token: Token = self.eat(TokenType.STRING)
        selectors.append(selector_token.value)
        
        # Parse additional selectors (optional)
        while self.current_token and self.current_token.type == TokenType.COMMA:
            self.eat(TokenType.COMMA)  # Eat the comma
            selector_token = self.eat(TokenType.STRING)
            selectors.append(selector_token.value)
            
        return selectors

    def parse_element_capture(self) -> Optional[str]:
        """Parse an optional 'as @variable' clause."""
        if self.current_token and self.current_token.type == TokenType.AS:
            self.eat(TokenType.AS)
            var_token: Token = self.eat(TokenType.IDENTIFIER)
            var_name: str = var_token.value
            
            # Validate that the variable name starts with @
            if not var_name.startswith('@'):
                raise SyntaxError(f"Element variable name must start with @ at line {var_token.line}, column {var_token.column}")
            
            return var_name
        return None

    # ======================================================================
    # BASIC STATEMENTS
    # ======================================================================

    def parse_goto_url(self) -> ASTNode:
        """Parse a goto_url statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'goto_url'
        
        # We expect a string argument (the URL)
        url_token: Token = self.eat(TokenType.STRING)
        
        return ASTNode(
            type=NodeType.GOTO_URL,
            line=token.line,
            column=token.column,
            url=url_token.value
        )
    
    def parse_goto_href(self) -> ASTNode:
        """Parse a goto_href statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER) # Eat 'goto_href'

        # Parse the selector list
        selectors: List[str] = self.parse_selector_list()

        return ASTNode(
            type=NodeType.GOTO_HREF,
            line=token.line,
            column=token.column,
            selectors=selectors
        )

    def parse_extract(self) -> ASTNode:
        """Parse an extract statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'extract'
        
        # We expect a string argument (column name)
        column_name_token: Token = self.eat(TokenType.STRING)
        
        # Parse the selector list
        selectors: List[str] = self.parse_selector_list()
        
        return ASTNode(
            type=NodeType.EXTRACT,
            line=token.line,
            column=token.column,
            column_name=column_name_token.value,
            selectors=selectors
        )

    def parse_extract_list(self) -> ASTNode:
        """Parse an extract_list statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)

        # We expect a string argument (column name)
        column_name_token: Token = self.eat(TokenType.STRING)

        # Parse the selector list
        selectors: List[str] = self.parse_selector_list()

        return ASTNode(
            type=NodeType.EXTRACT_LIST,
            line=token.line,
            column=token.column,
            column_name=column_name_token.value,
            selectors=selectors
        )

    def parse_extract_attribute(self) -> ASTNode:
        """Parse an extract_attribute statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'extract_attribute'
        
        # We expect two string arguments (column name, attribute)
        column_name_token: Token = self.eat(TokenType.STRING)
        attribute_token: Token = self.eat(TokenType.STRING)
        
        # Parse the selector list
        selectors: List[str] = self.parse_selector_list()
        
        return ASTNode(
            type=NodeType.EXTRACT_ATTRIBUTE,
            line=token.line,
            column=token.column,
            column_name=column_name_token.value,
            attribute=attribute_token.value,
            selectors=selectors
        )
    
    def parse_extract_attribute_list(self) -> ASTNode:
        """Parse an extract_attribute_list statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)

        # We expect two string arguments (column name, attribute)
        column_name_token: Token = self.eat(TokenType.STRING)
        attribute_token: Token = self.eat(TokenType.STRING)

        # Parse the selector list
        selectors: List[str] = self.parse_selector_list()

        return ASTNode(
            type=NodeType.EXTRACT_ATTRIBUTE_LIST,
            line=token.line,
            column=token.column,
            column_name=column_name_token.value,
            attribute=attribute_token.value,
            selectors=selectors
        )

    def parse_save_row(self) -> ASTNode:
        """Parse a save_row statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'save_row'
        
        return ASTNode(
            type=NodeType.SAVE_ROW,
            line=token.line,
            column=token.column
        )
    
    def parse_clear_row(self) -> ASTNode:
        """Parse a clear_row statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER) # Eat 'clear_row'

        return ASTNode(
            type=NodeType.CLEAR_ROW,
            line=token.line,
            column=token.column
        )

    def parse_set_field(self) -> ASTNode:
        """Parse a set_field statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'set_field'
        
        # We expect two string arguments (column name and value)
        column_name_token: Token = self.eat(TokenType.STRING)
        value_token: Token = self.eat(TokenType.STRING)
        
        return ASTNode(
            type=NodeType.SET_FIELD,
            line=token.line,
            column=token.column,
            column_name=column_name_token.value,
            value=value_token.value
        )

    def parse_click(self) -> ASTNode:
        """Parse a click statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER) # Eat 'click'

        # Parse the selector list
        selectors: List[str] = self.parse_selector_list()

        return ASTNode(
            type=NodeType.CLICK,
            line=token.line,
            column=token.column,
            selectors=selectors
        )

    def parse_log(self) -> ASTNode:
        """Parse a log statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER) # Eat 'log'

        # We expect a string argument (log message)
        message_token: Token = self.eat(TokenType.STRING)

        return ASTNode(
            type=NodeType.LOG,
            line=token.line,
            column=token.column,
            message=message_token.value
        )
    
    def parse_throw(self) -> ASTNode:
        """Parse a throw statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER) # Eat 'throw'

        # We expect a string argument (error message)
        message_token: Token = self.eat(TokenType.STRING)

        return ASTNode(
            type=NodeType.THROW,
            line=token.line,
            column=token.column,
            message=message_token.value
        )
    
    def parse_timestamp(self) -> ASTNode:
        """Parse a timestamp statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER) # Eat 'timestamp'

        # We expect a string argument (column name)
        column_name_token: Token = self.eat(TokenType.STRING)

        return ASTNode(
            type=NodeType.TIMESTAMP,
            line=token.line,
            column=token.column,
            column_name=column_name_token.value
        )

    def parse_history_forward(self) -> ASTNode:
        """Parse a history_forward statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER) # Eat 'history_forward'

        return ASTNode(
            type=NodeType.HISTORY_FORWARD,
            line=token.line,
            column=token.column
        )
    
    def parse_history_back(self) -> ASTNode:
        """Parse a history_back statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER) # Eat 'history_back'

        return ASTNode(
            type=NodeType.HISTORY_BACK,
            line=token.line,
            column=token.column
        )

    def parse_exit(self) -> ASTNode:
        """Parse an exit statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'exit'
        
        return ASTNode(
            type=NodeType.EXIT,
            line=token.line,
            column=token.column
        )

    # ======================================================================
    # CONTROL FLOW STATEMENTS
    # ======================================================================

    def parse_if_statement(self) -> ASTNode:
        """Parse an if statement with optional else_if and else clauses."""
        token: Token = self.current_token
        self.eat(TokenType.IF)
        
        # Parse the condition
        condition: ASTNode = self.parse_condition()
        
        # We expect at least one newline after the condition
        if self.current_token.type != TokenType.NEWLINE:
            raise SyntaxError(f"Expected newline after condition at line {self.current_token.line}")
        self.skip_newlines()  # Skip all consecutive newlines
        
        # Parse the true branch (statements to execute if condition is true)
        true_branch: List[ASTNode] = []
        while (self.current_token and 
               self.current_token.type not in 
               (TokenType.END_IF, TokenType.ELSE, TokenType.ELSE_IF)):
            statement = self.parse_statement()
            if statement:
                true_branch.append(statement)
            self.skip_newlines()
        
        # Parse any else_if branches
        else_if_branches: List[Tuple[ASTNode, List[ASTNode]]] = []
        while self.current_token and self.current_token.type == TokenType.ELSE_IF:
            self.eat(TokenType.ELSE_IF)
            
            # Parse the else_if condition
            else_if_condition: ASTNode = self.parse_condition()
            
            # We expect at least one newline after the condition
            if self.current_token.type != TokenType.NEWLINE:
                raise SyntaxError(f"Expected newline after else_if condition at line {self.current_token.line}")
            self.skip_newlines()  # Skip all consecutive newlines
            
            # Parse the else_if branch statements
            else_if_statements: List[ASTNode] = []
            while (self.current_token and 
                   self.current_token.type not in 
                   (TokenType.END_IF, TokenType.ELSE, TokenType.ELSE_IF)):
                statement = self.parse_statement()
                if statement:
                    else_if_statements.append(statement)
                self.skip_newlines()
                
            else_if_branches.append((else_if_condition, else_if_statements))
        
        # Parse the else branch if it exists
        false_branch: List[ASTNode] = []
        if self.current_token and self.current_token.type == TokenType.ELSE:
            self.eat(TokenType.ELSE)
            self.skip_newlines()  # Skip newlines after else
            
            while self.current_token and self.current_token.type != TokenType.END_IF:
                statement = self.parse_statement()
                if statement:
                    false_branch.append(statement)
                self.skip_newlines()
        
        # We expect end_if at the end of the if statement
        self.eat(TokenType.END_IF)
        
        return ASTNode(
            type=NodeType.IF,
            line=token.line,
            column=token.column,
            condition=condition,
            true_branch=true_branch,
            else_if_branches=else_if_branches if else_if_branches else None,
            false_branch=false_branch if false_branch else None
        )

    def parse_foreach_statement(self) -> ASTNode:
        """Parse a foreach statement."""
        token: Token = self.current_token
        self.eat(TokenType.FOREACH)
        
        # Parse the selector list
        selectors: List[str] = self.parse_selector_list()
        
        # Parse 'as @variable'
        self.eat(TokenType.AS)
        var_token: Token = self.eat(TokenType.IDENTIFIER)
        element_var_name: str = var_token.value
        
        # Validate that the variable name starts with @
        if not element_var_name.startswith('@'):
            raise SyntaxError(f"Element variable name must start with @ at line {var_token.line}, column {var_token.column}")
        
        # We expect at least one newline after the foreach declaration
        if self.current_token.type != TokenType.NEWLINE:
            raise SyntaxError(f"Expected newline after foreach declaration at line {self.current_token.line}")
        self.skip_newlines()  # Skip all consecutive newlines
        
        # Parse the loop body
        loop_body: List[ASTNode] = []
        while (self.current_token and 
            self.current_token.type != TokenType.END_FOREACH):
            statement = self.parse_statement()
            if statement:
                loop_body.append(statement)
            self.skip_newlines()
        
        # We expect end_foreach at the end
        self.eat(TokenType.END_FOREACH)
        
        return ASTNode(
            type=NodeType.FOREACH,
            line=token.line,
            column=token.column,
            selectors=selectors,
            element_var_name=element_var_name,
            loop_body=loop_body
        )

    def parse_while_statement(self) -> ASTNode:
        """Parse a while statement."""
        token: Token = self.current_token
        self.eat(TokenType.WHILE)
        
        # Parse the condition
        condition: ASTNode = self.parse_condition()
        
        # We expect at least one newline after the condition
        if self.current_token.type != TokenType.NEWLINE:
            raise SyntaxError(f"Expected newline after while condition at line {self.current_token.line}")
        self.skip_newlines()  # Skip all consecutive newlines
        
        # Parse the loop body
        loop_body: List[ASTNode] = []
        while (self.current_token and 
            self.current_token.type != TokenType.END_WHILE):
            statement = self.parse_statement()
            if statement:
                loop_body.append(statement)
            self.skip_newlines()
        
        # We expect end_while at the end
        self.eat(TokenType.END_WHILE)
        
        return ASTNode(
            type=NodeType.WHILE,
            line=token.line,
            column=token.column,
            condition=condition,
            loop_body=loop_body
        )
    
    def parse_select(self) -> ASTNode:
        """Parse a select statement."""
        token: Token = self.current_token
        self.eat(TokenType.SELECT)  # Eat 'select'
        
        # Parse the selector list
        selectors: List[str] = self.parse_selector_list()
        
        # Parse mandatory 'as @variable'
        element_var_name: Optional[str] = self.parse_element_capture()
        if not element_var_name:
            raise SyntaxError(f"Select statement requires 'as @variable' at line {token.line}")
        
        return ASTNode(
            type=NodeType.SELECT,
            line=token.line,
            column=token.column,
            selectors=selectors,
            element_var_name=element_var_name
        )

    # ======================================================================
    # CONDITION PARSING
    # ======================================================================

    def parse_exists_condition(self) -> ASTNode:
        """Parse an 'exists' condition."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'exists'
        
        # Parse the selector list
        selectors: List[str] = self.parse_selector_list()
        
        return ASTNode(
            type=NodeType.CONDITION_EXISTS,
            line=token.line,
            column=token.column,
            selectors=selectors
        )

    def parse_condition_factor(self) -> ASTNode:
        """Parse a condition factor (primary condition)."""
        if self.current_token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.parse_condition()
            self.eat(TokenType.RPAREN)
            return node
        elif self.current_token.type == TokenType.NOT:
            token = self.current_token
            self.eat(TokenType.NOT)
            operand = self.parse_condition_factor()
            return ASTNode(
                type=NodeType.CONDITION_NOT,
                line=token.line,
                column=token.column,
                operand=operand
            )
        elif self.current_token.type == TokenType.IDENTIFIER and self.current_token.value == 'exists':
            return self.parse_exists_condition()
        elif self.current_token.type == TokenType.IS_EMPTY:
            return self.parse_is_empty_condition()
        else:
            raise SyntaxError(f"Unexpected token in condition: {self.current_token.value}")
    
    def parse_condition_term(self) -> ASTNode:
        """Parse a condition term (AND expressions)."""
        node: ASTNode = self.parse_condition_factor()
        
        while (self.current_token and self.current_token.type == TokenType.AND):
            token: Token = self.current_token
            self.eat(TokenType.AND)
            
            node = ASTNode(
                type=NodeType.CONDITION_AND,
                line=token.line,
                column=token.column,
                left=node,
                right=self.parse_condition_factor()
            )
            
        return node
    
    def parse_condition(self) -> ASTNode:
        """Parse a condition (OR expressions)."""
        node: ASTNode = self.parse_condition_term()
        
        while (self.current_token and self.current_token.type == TokenType.OR):
            token: Token = self.current_token
            self.eat(TokenType.OR)
            
            node = ASTNode(
                type=NodeType.CONDITION_OR,
                line=token.line,
                column=token.column,
                left=node,
                right=self.parse_condition_term()
            )
            
        return node

    # ======================================================================
    # PROGRAM STRUCTURE
    # ======================================================================
    
    def parse_statement(self) -> Optional[ASTNode]:
        """Parse a single statement."""
        # Skip any newlines before the statement
        self.skip_newlines()
        
        if not self.current_token or self.current_token.type == TokenType.EOF:
            return None
            
        # Check statement type based on the current token
        if self.current_token.type == TokenType.IDENTIFIER:
            identifier = self.current_token.value
            
            # Parse the appropriate statement type based on keyword
            if identifier == 'goto_url':
                node = self.parse_goto_url()
            elif identifier == 'goto_href':
                node = self.parse_goto_href()
            elif identifier == 'extract':
                node = self.parse_extract()
            elif identifier == 'extract_list':
                node = self.parse_extract_list()
            elif identifier == 'extract_attribute':
                node = self.parse_extract_attribute()
            elif identifier == 'extract_attribute_list':
                node = self.parse_extract_attribute_list()
            elif identifier == 'save_row':
                node = self.parse_save_row()
            elif identifier == 'clear_row':
                node = self.parse_clear_row()
            elif identifier == 'set_field':
                node = self.parse_set_field()
            elif identifier == 'log':
                node = self.parse_log()
            elif identifier == 'history_forward':
                node = self.parse_history_forward()
            elif identifier == 'history_back':
                node = self.parse_history_back()
            elif identifier == 'click':
                node = self.parse_click()
            elif identifier == 'throw':
                node = self.parse_throw()
            elif identifier == 'timestamp':
                node = self.parse_timestamp()
            elif identifier == 'exit':
                node = self.parse_exit()
            else:
                raise SyntaxError(f"Unknown command: {identifier}")
        elif self.current_token.type == TokenType.IF:
            node = self.parse_if_statement()
        elif self.current_token.type == TokenType.FOREACH:
            node = self.parse_foreach_statement()
        elif self.current_token.type == TokenType.WHILE:
            node = self.parse_while_statement()
        elif self.current_token.type == TokenType.SELECT:
            node = self.parse_select()
        elif self.current_token.type == TokenType.DATA_SCHEMA:
            node = self.parse_data_schema()
        elif self.current_token.type == TokenType.NEWLINE:
            self.eat(TokenType.NEWLINE)
            return None
        else:
            raise SyntaxError(f"Unexpected token: {self.current_token.value}")
        
        # Expect a newline after each statement (or EOF)
        if self.current_token and self.current_token.type not in (TokenType.NEWLINE, TokenType.EOF):
            raise SyntaxError(f"Expected newline after statement, got: {self.current_token.value}")
        
        # Skip the newline if there is one
        if self.current_token and self.current_token.type == TokenType.NEWLINE:
            self.eat(TokenType.NEWLINE)
            
        return node

    def parse(self) -> ASTNode:
        """Parse the tokens into an AST."""
        # Create a root program node
        root = ASTNode(
            type=NodeType.PROGRAM,
            line=1,
            column=1,
            children=[]
        )
        
        # Parse statements until we reach the end of file
        while self.current_token and self.current_token.type != TokenType.EOF:
            statement = self.parse_statement()
            if statement:
                root.children.append(statement)
        
        return root

    def parse_data_schema(self) -> ASTNode:
        """Parse a data_schema declaration block."""
        token: Token = self.current_token
        self.eat(TokenType.DATA_SCHEMA)  # Eat 'data_schema'
        self.skip_newlines()  # Skip newlines after data_schema
        
        # Create the data schema node
        schema_node = ASTNode(
            type=NodeType.DATA_SCHEMA,
            line=token.line,
            column=token.column,
            children=[]
        )
        
        # Parse variable declarations until end_schema
        while self.current_token and self.current_token.type != TokenType.END_SCHEMA:
            if self.current_token.type == TokenType.STRING:
                # Get the column name
                column_token = self.current_token
                column_name = column_token.value
                self.eat(TokenType.STRING)
                
                # Check for optional 'as $variable'
                var_name = None
                if self.current_token and self.current_token.type == TokenType.AS:
                    self.eat(TokenType.AS)
                    if self.current_token and self.current_token.type == TokenType.VARIABLE:
                        var_name = self.current_token.value
                        self.eat(TokenType.VARIABLE)
                    else:
                        raise SyntaxError(f"Expected $variable after 'as' at line {column_token.line}")
                else:
                    # Auto-convert to $variable_name by replacing spaces with underscores
                    var_name = '$' + column_name.lower().replace(' ', '_')
                
                # Create variable declaration node
                var_node = ASTNode(
                    type=NodeType.VARIABLE_DECLARATION,
                    line=column_token.line,
                    column=column_token.column,
                    column_name=column_name,
                    value=var_name
                )
                
                schema_node.children.append(var_node)
                
                # Expect newline after declaration
                if self.current_token and self.current_token.type != TokenType.NEWLINE:
                    raise SyntaxError(f"Expected newline after variable declaration at line {column_token.line}")
                self.skip_newlines()
            else:
                raise SyntaxError(f"Expected string literal for column name at line {self.current_token.line}")
        
        # Eat end_schema
        self.eat(TokenType.END_SCHEMA)
        
        return schema_node

    def parse_is_empty_condition(self) -> ASTNode:
        """Parse an 'is_empty' condition."""
        token: Token = self.current_token
        self.eat(TokenType.IS_EMPTY)
        
        # We expect a variable reference or a string
        value = None
        if self.current_token.type == TokenType.VARIABLE:
            value = self.current_token.value
            self.eat(TokenType.VARIABLE)
        elif self.current_token.type == TokenType.STRING:
            value = self.current_token.value
            self.eat(TokenType.STRING)
        else:
            raise SyntaxError(f"Expected variable or string after is_empty at line {token.line}")
        
        return ASTNode(
            type=NodeType.CONDITION_IS_EMPTY,
            line=token.line,
            column=token.column,
            value=value
        )