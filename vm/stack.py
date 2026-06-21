from __future__ import annotations


class Stack:
    def __init__(self) -> None:
        self._items: list[object] = []

    def push(self, value: object) -> None:
        self._items.append(value)

    def pop(self) -> object:
        if not self._items:
            raise RuntimeError("Stack underflow")
        return self._items.pop()

    def peek(self) -> object:
        if not self._items:
            raise RuntimeError("Stack is empty")
        return self._items[-1]

    def is_empty(self) -> bool:
        return not self._items

    def __len__(self) -> int:
        return len(self._items)

