from __future__ import annotations

from .token_type import TokenType


KEYWORDS = {
    "let": TokenType.LET,
    "fn": TokenType.FN,
    "struct": TokenType.STRUCT,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "return": TokenType.RETURN,
    "print": TokenType.PRINT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "nil": TokenType.NIL,
    "and": TokenType.AND,
    "or": TokenType.OR,
}
