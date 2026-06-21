from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .opcode import Opcode


@dataclass(slots=True)
class Instruction:
    opcode: Opcode
    operands: tuple[Any, ...] = ()


@dataclass(slots=True)
class BytecodeFunction:
    name: str
    params: list[str] = field(default_factory=list)
    instructions: list[Instruction] = field(default_factory=list)


@dataclass(slots=True)
class BytecodeProgram:
    main: BytecodeFunction
    functions: dict[str, BytecodeFunction] = field(default_factory=dict)

