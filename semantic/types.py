from __future__ import annotations

from enum import Enum, auto


class TypeKind(Enum):
    ANY = auto()
    UNKNOWN = auto()
    NIL = auto()
    BOOLEAN = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    FUNCTION = auto()

