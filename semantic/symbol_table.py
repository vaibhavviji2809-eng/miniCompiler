from __future__ import annotations

from dataclasses import dataclass, field

from .scope import Scope
from .types import ANY_TYPE, Type, TypeKind, UNKNOWN_TYPE


@dataclass
class Symbol:
    name: str
    type: Type = ANY_TYPE
    scope: str = "global"
    location: int | None = None
    params: list[Type] = field(default_factory=list)
    return_type: Type = UNKNOWN_TYPE


class SymbolTable:
    def __init__(self) -> None:
        self.global_scope = Scope("global")
        self.current_scope = self.global_scope

    def push_scope(self, name: str) -> Scope:
        self.current_scope = Scope(name=name, parent=self.current_scope, depth=self.current_scope.depth + 1)
        return self.current_scope

    def pop_scope(self) -> Scope:
        if self.current_scope.parent is None:
            return self.current_scope
        scope = self.current_scope
        self.current_scope = self.current_scope.parent
        return scope

    def insert(self, symbol: Symbol) -> Symbol:
        if self.current_scope.resolve_local(symbol.name) is not None:
            raise ValueError(f"Duplicate symbol {symbol.name}")
        self.current_scope.define(symbol)
        return symbol

    def lookup(self, name: str) -> Symbol | None:
        result = self.current_scope.resolve(name)
        return result if isinstance(result, Symbol) else None

    def remove(self, name: str) -> None:
        self.current_scope.remove(name)
