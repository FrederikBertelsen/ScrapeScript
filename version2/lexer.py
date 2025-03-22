import re
from enum import Enum, auto
from dataclasses import dataclass

class TokenType(Enum):
    IDENTIFIER = auto()      # goto_url, extract, etc.
    STRING = auto()          # 'text inside quotes'
    NEWLINE = auto()         # Line break
    EOF = auto()             # End of file

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.current_char = self.text[0] if text else None

    def advance(self):
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

    def skip_whitespace(self):
        """Skip whitespace characters but not newlines."""
        while self.current_char and self.current_char.isspace() and self.current_char != '\n':
            self.advance()

    def identifier(self):
        """Read an identifier (command name)."""
        result = ''
        start_column = self.column
        
        while self.current_char and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
            
        return Token(TokenType.IDENTIFIER, result, self.line, start_column)

    def string(self):
        """Read a string literal."""
        quote_char = self.current_char  # Store whether ' or " was used
        start_column = self.column
        self.advance()  # Skip the opening quote
        
        result = ''
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

    def get_next_token(self):
        """Get the next token from the input."""
        while self.current_char:
            # Skip whitespace
            if self.current_char.isspace() and self.current_char != '\n':
                self.skip_whitespace()
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
                
            # If we get here, we have an invalid character
            raise SyntaxError(f"Invalid character '{self.current_char}' at line {self.line}, column {self.column}")
            
        # If we get here, we're at the end of the file
        return Token(TokenType.EOF, '', self.line, self.column)

    def tokenize(self):
        """Convert the entire input to a list of tokens."""
        tokens = []
        token = self.get_next_token()
        
        while token.type != TokenType.EOF:
            tokens.append(token)
            token = self.get_next_token()
            
        tokens.append(token)  # Add the EOF token
        return tokens