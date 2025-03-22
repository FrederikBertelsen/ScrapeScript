from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Any, Dict, Union, Tuple
from lexer import TokenType, Token

class NodeType(Enum):
    GOTO_URL = auto()
    EXTRACT = auto()
    SAVE_ROW = auto()
    SET_FIELD = auto()  # New node type for set_field
    EXIT = auto()
    PROGRAM = auto() 
    IF = auto()      
    CONDITION_EXISTS = auto()
    CONDITION_AND = auto()    
    CONDITION_OR = auto()      
    CONDITION_NOT = auto()     

@dataclass
class ASTNode:
    type: NodeType
    line: int
    column: int
    
    # Additional fields for specific node types
    url: Optional[str] = None  # For GOTO_URL
    column_name: Optional[str] = None  # For EXTRACT and SET_FIELD
    value: Optional[str] = None  # For SET_FIELD
    selector: Optional[str] = None  # For single selector nodes
    selectors: Optional[List[str]] = None  # For nodes that support multiple selectors
    condition: Optional[Any] = None  # For IF nodes
    true_branch: Optional[List[Any]] = None  # For IF nodes
    elseif_branches: Optional[List[Tuple[Any, List[Any]]]] = None  # For IF nodes with elseif
    false_branch: Optional[List[Any]] = None  # For IF nodes
    left: Optional[Any] = None  # For logical operations
    right: Optional[Any] = None  # For logical operations
    operand: Optional[Any] = None  # For NOT
    children: Optional[List[Any]] = None  # For PROGRAM

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[0] if tokens else None

    def advance(self):
        """Move to the next token."""
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None

    def eat(self, token_type):
        """Consume the current token if it matches the expected type."""
        if self.current_token and self.current_token.type == token_type:
            token = self.current_token
            self.advance()
            return token
        else:
            expected = token_type.name
            found = self.current_token.type.name if self.current_token else "EOF"
            raise SyntaxError(f"Expected {expected}, found {found} at line {self.current_token.line}, column {self.current_token.column}")

    def skip_newlines(self):
        """Skip any newline tokens."""
        while self.current_token and self.current_token.type == TokenType.NEWLINE:
            self.advance()

    def parse_selector_list(self):
        """Parse a list of selectors (string literals separated by commas)."""
        selectors = []
        
        # Parse the first selector (required)
        selector_token = self.eat(TokenType.STRING)
        selectors.append(selector_token.value)
        
        # Parse additional selectors (optional)
        while self.current_token and self.current_token.type == TokenType.COMMA:
            self.eat(TokenType.COMMA)  # Eat the comma
            selector_token = self.eat(TokenType.STRING)
            selectors.append(selector_token.value)
            
        return selectors

    def parse_goto_url(self):
        """Parse a goto_url statement."""
        token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'goto_url'
        
        # We expect a string argument (the URL)
        url_token = self.eat(TokenType.STRING)
        
        return ASTNode(
            type=NodeType.GOTO_URL,
            line=token.line,
            column=token.column,
            url=url_token.value
        )

    def parse_extract(self):
        """Parse an extract statement."""
        token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'extract'
        
        # We expect a string argument (column name)
        column_name_token = self.eat(TokenType.STRING)
        
        # Parse the selector list
        selectors = self.parse_selector_list()
        
        return ASTNode(
            type=NodeType.EXTRACT,
            line=token.line,
            column=token.column,
            column_name=column_name_token.value,
            selectors=selectors
        )

    def parse_save_row(self):
        """Parse a save_row statement."""
        token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'save_row'
        
        return ASTNode(
            type=NodeType.SAVE_ROW,
            line=token.line,
            column=token.column
        )

    def parse_exit(self):
        """Parse an exit statement."""
        token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'exit'
        
        return ASTNode(
            type=NodeType.EXIT,
            line=token.line,
            column=token.column
        )
        
    def parse_exists_condition(self):
        """Parse an 'exists' condition."""
        token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'exists'
        
        # Parse the selector list
        selectors = self.parse_selector_list()
        
        return ASTNode(
            type=NodeType.CONDITION_EXISTS,
            line=token.line,
            column=token.column,
            selectors=selectors
        )
        
    def parse_condition_factor(self):
        """Parse a condition factor (primary condition)."""
        if self.current_token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.parse_condition()
            self.eat(TokenType.RPAREN)
            return node
        elif self.current_token.type == TokenType.NOT:
            token = self.current_token
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
    
    def parse_condition_term(self):
        """Parse a condition term (AND expressions)."""
        node = self.parse_condition_factor()
        
        while (self.current_token and self.current_token.type == TokenType.AND):
            token = self.current_token
            self.eat(TokenType.AND)
            
            node = ASTNode(
                type=NodeType.CONDITION_AND,
                line=token.line,
                column=token.column,
                left=node,
                right=self.parse_condition_factor()
            )
            
        return node
    
    def parse_condition(self):
        """Parse a condition (OR expressions)."""
        node = self.parse_condition_term()
        
        while (self.current_token and self.current_token.type == TokenType.OR):
            token = self.current_token
            self.eat(TokenType.OR)
            
            node = ASTNode(
                type=NodeType.CONDITION_OR,
                line=token.line,
                column=token.column,
                left=node,
                right=self.parse_condition_term()
            )
            
        return node

    def parse_if_statement(self):
        """Parse an if statement with optional elseif and else clauses."""
        token = self.current_token
        self.eat(TokenType.IF)
        
        # Parse the condition
        condition = self.parse_condition()
        
        # We expect at least one newline after the condition
        if self.current_token.type != TokenType.NEWLINE:
            raise SyntaxError(f"Expected newline after condition at line {self.current_token.line}")
        self.skip_newlines()  # Skip all consecutive newlines
        
        # Parse the true branch (statements to execute if condition is true)
        true_branch = []
        while (self.current_token and 
               self.current_token.type not in 
               (TokenType.ENDIF, TokenType.ELSE, TokenType.ELSEIF)):
            statement = self.parse_statement()
            if statement:
                true_branch.append(statement)
            self.skip_newlines()
        
        # Parse any elseif branches
        elseif_branches = []
        while self.current_token and self.current_token.type == TokenType.ELSEIF:
            self.eat(TokenType.ELSEIF)
            
            # Parse the elseif condition
            elseif_condition = self.parse_condition()
            
            # We expect at least one newline after the condition
            if self.current_token.type != TokenType.NEWLINE:
                raise SyntaxError(f"Expected newline after elseif condition at line {self.current_token.line}")
            self.skip_newlines()  # Skip all consecutive newlines
            
            # Parse the elseif branch statements
            elseif_statements = []
            while (self.current_token and 
                   self.current_token.type not in 
                   (TokenType.ENDIF, TokenType.ELSE, TokenType.ELSEIF)):
                statement = self.parse_statement()
                if statement:
                    elseif_statements.append(statement)
                self.skip_newlines()
                
            elseif_branches.append((elseif_condition, elseif_statements))
        
        # Parse the else branch if it exists
        false_branch = []
        if self.current_token and self.current_token.type == TokenType.ELSE:
            self.eat(TokenType.ELSE)
            self.skip_newlines()  # Skip newlines after else
            
            while self.current_token and self.current_token.type != TokenType.ENDIF:
                statement = self.parse_statement()
                if statement:
                    false_branch.append(statement)
                self.skip_newlines()
        
        # We expect endif at the end of the if statement
        self.eat(TokenType.ENDIF)
        
        return ASTNode(
            type=NodeType.IF,
            line=token.line,
            column=token.column,
            condition=condition,
            true_branch=true_branch,
            elseif_branches=elseif_branches if elseif_branches else None,
            false_branch=false_branch if false_branch else None
        )

    def parse_set_field(self):
        """Parse a set_field statement."""
        token = self.current_token
        self.eat(TokenType.IDENTIFIER)  # Eat 'set_field'
        
        # We expect two string arguments (column name and value)
        column_name_token = self.eat(TokenType.STRING)
        value_token = self.eat(TokenType.STRING)
        
        return ASTNode(
            type=NodeType.SET_FIELD,
            line=token.line,
            column=token.column,
            column_name=column_name_token.value,
            value=value_token.value
        )
    
    def parse_statement(self):
        """Parse a single statement."""
        if not self.current_token:
            return None
            
        if self.current_token.type == TokenType.IDENTIFIER:
            if self.current_token.value == 'goto_url':
                return self.parse_goto_url()
            elif self.current_token.value == 'extract':
                return self.parse_extract()
            elif self.current_token.value == 'save_row':
                return self.parse_save_row()
            elif self.current_token.value == 'set_field':
                return self.parse_set_field()
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

    def parse(self):
        """Parse the entire program."""
        statements = []
        
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