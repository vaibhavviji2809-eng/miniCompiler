from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .token_type import TokenType


@dataclass(slots=True)
class Token:
    type: TokenType
    lexeme: str
    literal: Any
    line: int
    column: int

