from __future__ import annotations


class Heap:
    def __init__(self) -> None:
        self._objects: dict[int, object] = {}
        self._next_handle = 1

    def allocate(self, value: object) -> int:
        handle = self._next_handle
        self._next_handle += 1
        self._objects[handle] = value
        return handle

    def get(self, handle: int) -> object:
        return self._objects[handle]

    def set(self, handle: int, value: object) -> None:
        self._objects[handle] = value

    def free(self, handle: int) -> None:
        self._objects.pop(handle, None)

