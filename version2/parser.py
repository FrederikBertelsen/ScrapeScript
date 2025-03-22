from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Any, Dict
from lexer import TokenType, Token

class NodeType(Enum):
    GOTO_URL = auto()
    EXTRACT = auto()
    SAVE_ROW = auto()
    EXIT = auto()
    PROGRAM = auto()  # Root node representing the entire program

@dataclass
class ASTNode:
    type: NodeType
    line: int
    column: int
    
    # Additional fields for specific node types
    url: Optional[str] = None  # For GOTO_URL
    column_name: Optional[str] = None  # For EXTRACT
    selector: Optional[str] = None  # For EXTRACT
    children: List[Any] = None  # For PROGRAM

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
        
        # We expect two string arguments (column name and selector)
        column_name_token = self.eat(TokenType.STRING)
        selector_token = self.eat(TokenType.STRING)
        
        return ASTNode(
            type=NodeType.EXTRACT,
            line=token.line,
            column=token.column,
            column_name=column_name_token.value,
            selector=selector_token.value
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
            elif self.current_token.value == 'exit':
                return self.parse_exit()
            else:
                raise SyntaxError(f"Unknown command '{self.current_token.value}' at line {self.current_token.line}")
        
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