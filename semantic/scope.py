from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Scope:
    name: str
    parent: Scope | None = None
    depth: int = 0
    symbols: dict[str, object] = field(default_factory=dict)

    def define(self, symbol: object) -> None:
        self.symbols[getattr(symbol, "name")] = symbol

    def resolve_local(self, name: str) -> object | None:
        return self.symbols.get(name)

    def resolve(self, name: str) -> object | None:
        scope: Scope | None = self
        while scope is not None:
            symbol = scope.resolve_local(name)
            if symbol is not None:
                return symbol
            scope = scope.parent
        return None

    def remove(self, name: str) -> None:
        self.symbols.pop(name, None)

