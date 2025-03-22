from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Any, Dict, Union, Tuple, TypeVar, cast
from lexer import TokenType, Token

class NodeType(Enum):
    GOTO_URL = auto()
    EXTRACT = auto()
    EXTRACT_LIST = auto()
    EXTRACT_ATTRIBUTE = auto()
    EXTRACT_ATTRIBUTE_LIST = auto()
    SAVE_ROW = auto()
    CLEAR_ROW = auto()
    SET_FIELD = auto()
    LOG = auto()
    HISTORY_FORWARD = auto()
    HISTORY_BACK = auto()
    CLICK = auto()
    THROW = auto()
    TIMESTAMP = auto()
    EXIT = auto()
    PROGRAM = auto() 
    IF = auto()      
    CONDITION_EXISTS = auto()
    CONDITION_AND = auto()    
    CONDITION_OR = auto()      
    CONDITION_NOT = auto()     

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
    condition: Optional[ASTNodeT] = None  # For IF nodes
    true_branch: Optional[List[ASTNodeT]] = None  # For IF nodes
    else_if_branches: Optional[List[Tuple[ASTNodeT, List[ASTNodeT]]]] = None  # For IF nodes with else_if
    false_branch: Optional[List[ASTNodeT]] = None  # For IF nodes
    left: Optional[ASTNodeT] = None  # For logical operations
    right: Optional[ASTNodeT] = None  # For logical operations
    operand: Optional[ASTNodeT] = None  # For NOT
    children: Optional[List[ASTNodeT]] = None  # For PROGRAM

class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens: List[Token] = tokens
        self.pos: int = 0
        self.current_token: Optional[Token] = self.tokens[0] if tokens else None

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
            token: Token = self.current_token
            self.advance()
            return token
        else:
            expected = token_type.name
            found = self.current_token.type.name if self.current_token else "EOF"
            raise SyntaxError(f"Expected {expected}, found {found} at line {self.current_token.line}, column {self.current_token.column}")

    def skip_newlines(self) -> None:
        """Skip any newline tokens."""
        while self.current_token and self.current_token.type == TokenType.NEWLINE:
            self.advance()

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

    def parse_exit(self) -> ASTNode:
        """Parse an exit statement."""
        token: Token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'exit'
        
        return ASTNode(
            type=NodeType.EXIT,
            line=token.line,
            column=token.column
        )
        
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
            node: ASTNode = self.parse_condition()
            self.eat(TokenType.RPAREN)
            return node
        elif self.current_token.type == TokenType.NOT:
            token: Token = self.current_token
            self.eat(TokenType.NOT)
            return ASTNode(
                type=NodeType.CONDITION_NOT,
                line=token.line,
                column=token.column,
                operand=self.parse_condition_factor()
            )
        elif self.current_token.type == TokenType.IDENTIFIER and self.current_token.value == 'exists':
            return self.parse_exists_condition()
        else:
            raise SyntaxError(f"Expected condition at line {self.current_token.line}, column {self.current_token.column}")
    
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
    
    def parse_statement(self) -> Optional[ASTNode]:
        """Parse a single statement."""
        if not self.current_token:
            return None
            
        if self.current_token.type == TokenType.IDENTIFIER:
            if self.current_token.value == 'goto_url':
                return self.parse_goto_url()
            elif self.current_token.value == 'extract':
                return self.parse_extract()
            elif self.current_token.value == 'extract_list':
                return self.parse_extract_list()
            elif self.current_token.value == 'extract_attribute':
                return self.parse_extract_attribute()
            elif self.current_token.value == 'extract_attribute_list':
                return self.parse_extract_attribute_list()
            elif self.current_token.value == 'save_row':
                return self.parse_save_row()
            elif self.current_token.value == 'clear_row':
                return self.parse_clear_row()
            elif self.current_token.value == 'set_field':
                return self.parse_set_field()
            elif self.current_token.value == 'log':
                return self.parse_log()
            elif self.current_token.value == 'throw':
                return self.parse_throw()
            elif self.current_token.value == 'history_forward':
                return self.parse_history_forward()
            elif self.current_token.value == 'history_back':
                return self.parse_history_back()
            elif self.current_token.value == 'click':
                return self.parse_click()
            elif self.current_token.value == 'timestamp':
                return self.parse_timestamp()
            elif self.current_token.value == 'exit':
                return self.parse_exit()
            else:
                raise SyntaxError(f"Unknown command '{self.current_token.value}' at line {self.current_token.line}")
        
        # Handle if statements
        if self.current_token.type == TokenType.IF:
            return self.parse_if_statement()
        
        # Skip newlines between statements
        if self.current_token.type == TokenType.NEWLINE:
            self.skip_newlines()
            return self.parse_statement()
            
        # If we get here, we have an unexpected token
        raise SyntaxError(f"Unexpected token {self.current_token.type.name} at line {self.current_token.line}")

    def parse(self) -> ASTNode:
        """Parse the entire program."""
        statements: List[ASTNode] = []
        
        # Skip any leading newlines
        self.skip_newlines()
        
        # Parse statements until we reach the end of the file
        while self.current_token and self.current_token.type != TokenType.EOF:
            statement = self.parse_statement()
            if statement:
                statements.append(statement)
                
            # Skip newlines between statements
            self.skip_newlines()
            
        # Create a program node with all statements as children
        return ASTNode(
            type=NodeType.PROGRAM,
            line=1,
            column=1,
            children=statements
        )