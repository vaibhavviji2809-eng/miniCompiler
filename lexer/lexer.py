from __future__ import annotations

from typing import Any, Optional

from .keywords import KEYWORDS
from .token import Token
from .token_type import TokenType


class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source.lstrip("\ufeff")
        self.length = len(self.source)
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.start_column = 1

    def peek(self) -> str:
        if self.current >= self.length:
            return "\0"
        return self.source[self.current]

    def peek_next(self) -> str:
        index = self.current + 1
        if index >= self.length:
            return "\0"
        return self.source[index]

    def advance(self) -> str:
        char = self.source[self.current]
        self.current += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def match(self, expected: str) -> bool:
        if self.current >= self.length or self.source[self.current] != expected:
            return False
        self.advance()
        return True

    def is_at_end(self) -> bool:
        return self.current >= self.length

    def skip_whitespace(self) -> None:
        while not self.is_at_end():
            char = self.peek()
            if char in " \r\t":
                self.advance()
            elif char == "\n":
                self.advance()
            elif char == "/" and self.peek_next() in {"/", "*"}:
                self.skip_comment()
            else:
                break

    def skip_comment(self) -> None:
        if self.peek_next() == "/":
            while not self.is_at_end() and self.peek() != "\n":
                self.advance()
            return
        self.advance()
        self.advance()
        while not self.is_at_end():
            if self.peek() == "*" and self.peek_next() == "/":
                self.advance()
                self.advance()
                return
            self.advance()
        raise LexerError("Unterminated block comment")

    def string(self) -> Token:
        value = []
        while not self.is_at_end() and self.peek() != '"':
            char = self.advance()
            if char == "\\":
                escape = self.advance()
                escapes = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
                value.append(escapes.get(escape, escape))
            else:
                value.append(char)
        if self.is_at_end():
            raise LexerError("Unterminated string literal")
        self.advance()
        lexeme = self.source[self.start:self.current]
        return Token(TokenType.STRING, lexeme, "".join(value), self.line, self.start_column)

    def number(self) -> Token:
        while self.peek().isdigit():
            self.advance()
        if self.peek() == "." and self.peek_next().isdigit():
            self.advance()
            while self.peek().isdigit():
                self.advance()
            literal: Any = float(self.source[self.start:self.current])
        else:
            literal = int(self.source[self.start:self.current])
        lexeme = self.source[self.start:self.current]
        return Token(TokenType.NUMBER, lexeme, literal, self.line, self.start_column)

    def identifier(self) -> Token:
        while self.peek().isalnum() or self.peek() == "_":
            self.advance()
        lexeme = self.source[self.start:self.current]
        token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
        literal = None if token_type is not TokenType.IDENTIFIER else lexeme
        return Token(token_type, lexeme, literal, self.line, self.start_column)

    def next_token(self) -> Token:
        self.skip_whitespace()
        self.start = self.current
        self.start_column = self.column

        if self.is_at_end():
            return Token(TokenType.EOF, "", None, self.line, self.column)

        char = self.advance()
        if char == "(":
            return Token(TokenType.LEFT_PAREN, char, None, self.line, self.start_column)
        if char == ")":
            return Token(TokenType.RIGHT_PAREN, char, None, self.line, self.start_column)
        if char == "{":
            return Token(TokenType.LEFT_BRACE, char, None, self.line, self.start_column)
        if char == "}":
            return Token(TokenType.RIGHT_BRACE, char, None, self.line, self.start_column)
        if char == "[":
            return Token(TokenType.LEFT_BRACKET, char, None, self.line, self.start_column)
        if char == "]":
            return Token(TokenType.RIGHT_BRACKET, char, None, self.line, self.start_column)
        if char == ",":
            return Token(TokenType.COMMA, char, None, self.line, self.start_column)
        if char == ".":
            return Token(TokenType.DOT, char, None, self.line, self.start_column)
        if char == ";":
            return Token(TokenType.SEMICOLON, char, None, self.line, self.start_column)
        if char == ":":
            return Token(TokenType.COLON, char, None, self.line, self.start_column)
        if char == "+":
            return Token(TokenType.PLUS, char, None, self.line, self.start_column)
        if char == "-":
            return Token(TokenType.MINUS, char, None, self.line, self.start_column)
        if char == "*":
            return Token(TokenType.STAR, char, None, self.line, self.start_column)
        if char == "%":
            return Token(TokenType.PERCENT, char, None, self.line, self.start_column)
        if char == "!":
            return Token(TokenType.BANG_EQUAL if self.match("=") else TokenType.BANG, self.source[self.start:self.current], None, self.line, self.start_column)
        if char == "=":
            return Token(TokenType.EQUAL_EQUAL if self.match("=") else TokenType.EQUAL, self.source[self.start:self.current], None, self.line, self.start_column)
        if char == "<":
            return Token(TokenType.LESS_EQUAL if self.match("=") else TokenType.LESS, self.source[self.start:self.current], None, self.line, self.start_column)
        if char == ">":
            return Token(TokenType.GREATER_EQUAL if self.match("=") else TokenType.GREATER, self.source[self.start:self.current], None, self.line, self.start_column)
        if char == "/":
            return Token(TokenType.SLASH, char, None, self.line, self.start_column)
        if char == '"':
            return self.string()
        if char.isdigit():
            return self.number()
        if char.isalpha() or char == "_":
            return self.identifier()
        raise LexerError(f"Unexpected character {char!r} at line {self.line}, column {self.start_column}")

    def tokenize(self) -> list[Token]:
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.type is TokenType.EOF:
                return tokens
