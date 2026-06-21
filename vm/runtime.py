from __future__ import annotations

from dataclasses import dataclass, field

from ..bytecode.bytecode import BytecodeFunction, BytecodeProgram
from ..bytecode.opcode import Opcode
from .heap import Heap
from .stack import Stack


@dataclass
class Frame:
    name: str
    function: BytecodeFunction
    locals: dict[str, object] = field(default_factory=dict)
    stack: Stack = field(default_factory=Stack)
    ip: int = 0
    is_main: bool = False


class Runtime:
    def __init__(self, program: BytecodeProgram) -> None:
        self.program = program
        self.heap = Heap()
        self.globals: dict[str, object] = {}

    def create_frame(self, function_name: str, arguments: list[object] | None = None, is_main: bool = False) -> Frame:
        function = self.program.main if is_main else self.program.functions[function_name]
        locals_: dict[str, object] = {}
        if arguments is not None:
            for parameter, argument in zip(function.params, arguments):
                locals_[parameter] = argument
        return Frame(name=function_name, function=function, locals=locals_, is_main=is_main)

    def load_name(self, frame: Frame, name: str) -> object:
        if name in frame.locals:
            return frame.locals[name]
        if name in self.globals:
            return self.globals[name]
        raise RuntimeError(f"Undefined name {name}")

    def store_name(self, frame: Frame, name: str, value: object) -> None:
        if frame.is_main:
            self.globals[name] = value
        else:
            frame.locals[name] = value

