from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class TypeKind(Enum):
    ANY = auto()
    UNKNOWN = auto()
    NIL = auto()
    BOOLEAN = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    ARRAY = auto()
    STRUCT = auto()
    FUNCTION = auto()
    GENERIC = auto()


@dataclass(frozen=True)
class Type:
    kind: TypeKind
    name: str | None = None
    element_type: Type | None = None
    fields: tuple[tuple[str, Type], ...] = ()
    parameter_types: tuple[Type, ...] = ()
    return_type: Type | None = None
    type_parameters: tuple[str, ...] = ()
    metadata: tuple[tuple[str, Any], ...] = ()

    def __str__(self) -> str:
        if self.kind is TypeKind.ARRAY and self.element_type is not None:
            return f"{self.element_type}[]"
        if self.kind is TypeKind.STRUCT and self.name:
            return self.name
        if self.kind is TypeKind.FUNCTION:
            params = ", ".join(str(parameter) for parameter in self.parameter_types)
            return f"fn({params}) -> {self.return_type or PrimitiveType(TypeKind.ANY)}"
        if self.kind is TypeKind.GENERIC and self.name:
            return self.name
        if self.name:
            return self.name
        return self.kind.name.lower()


@dataclass(frozen=True)
class PrimitiveType(Type):
    def __init__(self, kind: TypeKind) -> None:
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "name", None)
        object.__setattr__(self, "element_type", None)
        object.__setattr__(self, "fields", ())
        object.__setattr__(self, "parameter_types", ())
        object.__setattr__(self, "return_type", None)
        object.__setattr__(self, "type_parameters", ())
        object.__setattr__(self, "metadata", ())


def array_of(element_type: Type) -> Type:
    return Type(kind=TypeKind.ARRAY, element_type=element_type)


def struct_type(name: str, fields: dict[str, Type]) -> Type:
    return Type(kind=TypeKind.STRUCT, name=name, fields=tuple(fields.items()))


def function_type(parameter_types: list[Type], return_type: Type) -> Type:
    return Type(kind=TypeKind.FUNCTION, parameter_types=tuple(parameter_types), return_type=return_type)


def generic_type(name: str) -> Type:
    return Type(kind=TypeKind.GENERIC, name=name)


ANY_TYPE = PrimitiveType(TypeKind.ANY)
UNKNOWN_TYPE = PrimitiveType(TypeKind.UNKNOWN)
NIL_TYPE = PrimitiveType(TypeKind.NIL)
BOOLEAN_TYPE = PrimitiveType(TypeKind.BOOLEAN)
INTEGER_TYPE = PrimitiveType(TypeKind.INTEGER)
FLOAT_TYPE = PrimitiveType(TypeKind.FLOAT)
STRING_TYPE = PrimitiveType(TypeKind.STRING)

