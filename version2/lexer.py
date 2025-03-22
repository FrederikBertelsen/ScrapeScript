import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Union

class TokenType(Enum):
    IDENTIFIER = auto()      # goto_url, extract, exists, etc.
    STRING = auto()          # 'text inside quotes'
    NEWLINE = auto()         # Line break
    IF = auto()              # if keyword
    ELSE_IF = auto()          # else_if keyword
    ELSE = auto()            # else keyword
    END_IF = auto()           # end_if keyword
    AND = auto()             # and operator
    OR = auto()              # or operator
    NOT = auto()             # not operator
    LPAREN = auto()          # (
    RPAREN = auto()          # )
    COMMA = auto()           # ,
    EOF = auto()             # End of file

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

class Lexer:
    # Reserved keywords
    RESERVED_KEYWORDS: dict[str, TokenType] = {
        'if': TokenType.IF,
        'else_if': TokenType.ELSE_IF,
        'else': TokenType.ELSE,
        'end_if': TokenType.END_IF,
        'and': TokenType.AND,
        'or': TokenType.OR,
        'not': TokenType.NOT,
    }

    def __init__(self, text: str) -> None:
        self.text: str = text
        self.pos: int = 0
        self.line: int = 1
        self.column: int = 1
        self.current_char: Optional[str] = self.text[0] if text else None

    def advance(self) -> None:
        """Move to the next character in the input."""
        self.pos += 1
        self.column += 1
        
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            if self.current_char == '\n':
                self.line += 1
                self.column = 1
            self.current_char = self.text[self.pos]

    def skip_whitespace(self) -> None:
        """Skip whitespace characters but not newlines."""
        while self.current_char and self.current_char.isspace() and self.current_char != '\n':
            self.advance()

    def skip_comment(self) -> None:
        """Skip comment (from # to end of line)."""
        # Skip the # character
        self.advance()
        
        # Skip all characters until we reach the end of line or end of file
        while self.current_char and self.current_char != '\n':
            self.advance()

    def identifier(self) -> Token:
        """Read an identifier (command name or keyword)."""
        result: str = ''
        start_column: int = self.column
        
        while self.current_char and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
            
        # Check if this is a reserved keyword
        token_type = self.RESERVED_KEYWORDS.get(result.lower(), TokenType.IDENTIFIER)
        return Token(token_type, result, self.line, start_column)

    def string(self) -> Token:
        """Read a string literal."""
        quote_char: str = self.current_char  # Store whether ' or " was used
        start_column: int = self.column
        self.advance()  # Skip the opening quote
        
        result: str = ''
        while self.current_char and self.current_char != quote_char:
            # Handle escape sequences
            if self.current_char == '\\' and self.pos + 1 < len(self.text):
                self.advance()
                if self.current_char == quote_char:
                    result += quote_char
                elif self.current_char == 'n':
                    result += '\n'
                elif self.current_char == 't':
                    result += '\t'
                elif self.current_char == '\\':
                    result += '\\'
                else:
                    result += '\\' + self.current_char
            else:
                result += self.current_char
            self.advance()
            
        if self.current_char is None:
            raise SyntaxError(f"Unterminated string at line {self.line}, column {start_column}")
            
        self.advance()  # Skip the closing quote
        return Token(TokenType.STRING, result, self.line, start_column)

    def get_next_token(self) -> Token:
        """Get the next token from the input."""
        while self.current_char:
            # Skip whitespace
            if self.current_char.isspace() and self.current_char != '\n':
                self.skip_whitespace()
                continue
                
            # Skip comments
            if self.current_char == '#':
                self.skip_comment()
                continue
                
            # Handle newlines
            if self.current_char == '\n':
                token = Token(TokenType.NEWLINE, '\n', self.line, self.column)
                self.advance()
                return token
                
            # Handle identifiers
            if self.current_char.isalpha() or self.current_char == '_':
                return self.identifier()
                
            # Handle string literals
            if self.current_char in ('"', "'"):
                return self.string()
                
            # Handle parentheses
            if self.current_char == '(':
                token = Token(TokenType.LPAREN, '(', self.line, self.column)
                self.advance()
                return token
                
            if self.current_char == ')':
                token = Token(TokenType.RPAREN, ')', self.line, self.column)
                self.advance()
                return token
                
            # Handle comma
            if self.current_char == ',':
                token = Token(TokenType.COMMA, ',', self.line, self.column)
                self.advance()
                return token
                
            # If we get here, we have an invalid character
            raise SyntaxError(f"Invalid character '{self.current_char}' at line {self.line}, column {self.column}")
            
        # If we get here, we're at the end of the file
        return Token(TokenType.EOF, '', self.line, self.column)

    def tokenize(self) -> List[Token]:
        """Convert the entire input to a list of tokens."""
        tokens: List[Token] = []
        token: Token = self.get_next_token()
        
        while token.type != TokenType.EOF:
            tokens.append(token)
            token = self.get_next_token()
            
        tokens.append(token)  # Add the EOF token
        return tokens