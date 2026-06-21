from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class IRInstruction:
    opcode: str
    operands: tuple[Any, ...] = ()


@dataclass(slots=True)
class IRFunction:
    name: str
    params: list[str] = field(default_factory=list)
    instructions: list[IRInstruction] = field(default_factory=list)


@dataclass(slots=True)
class IRProgram:
    main: IRFunction
    functions: dict[str, IRFunction] = field(default_factory=dict)

