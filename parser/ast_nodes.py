from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class Node:
    line: int = 0
    column: int = 0


@dataclass(slots=True)
class Statement(Node):
    pass


@dataclass(slots=True)
class Expression(Node):
    pass


@dataclass(slots=True)
class Program(Node):
    statements: list[Statement] = field(default_factory=list)


@dataclass(slots=True)
class Block(Statement):
    statements: list[Statement] = field(default_factory=list)


@dataclass(slots=True)
class VariableDeclaration(Statement):
    name: str = ""
    initializer: Optional[Expression] = None


@dataclass(slots=True)
class Assignment(Expression, Statement):
    target: str = ""
    value: Expression | None = None


@dataclass(slots=True)
class FunctionDeclaration(Statement):
    name: str = ""
    params: list[str] = field(default_factory=list)
    body: Block = field(default_factory=Block)


@dataclass(slots=True)
class IfStatement(Statement):
    condition: Expression | None = None
    then_branch: Block = field(default_factory=Block)
    else_branch: Optional[Block] = None


@dataclass(slots=True)
class WhileStatement(Statement):
    condition: Expression | None = None
    body: Block = field(default_factory=Block)


@dataclass(slots=True)
class ForStatement(Statement):
    initializer: Optional[Statement] = None
    condition: Optional[Expression] = None
    increment: Optional[Expression] = None
    body: Block = field(default_factory=Block)


@dataclass(slots=True)
class ReturnStatement(Statement):
    value: Optional[Expression] = None


@dataclass(slots=True)
class PrintStatement(Statement):
    value: Expression | None = None


@dataclass(slots=True)
class ExpressionStatement(Statement):
    expression: Expression | None = None


@dataclass(slots=True)
class BinaryExpression(Expression):
    left: Expression | None = None
    operator: Any = None
    right: Expression | None = None


@dataclass(slots=True)
class UnaryExpression(Expression):
    operator: Any = None
    operand: Expression | None = None


@dataclass(slots=True)
class Literal(Expression):
    value: Any = None


@dataclass(slots=True)
class Identifier(Expression):
    name: str = ""


@dataclass(slots=True)
class CallExpression(Expression):
    callee: Expression | None = None
    arguments: list[Expression] = field(default_factory=list)


@dataclass(slots=True)
class Grouping(Expression):
    expression: Expression | None = None

