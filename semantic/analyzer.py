from __future__ import annotations

from dataclasses import dataclass

from ..parser.ast_nodes import (
    Assignment,
    BinaryExpression,
    Block,
    CallExpression,
    Expression,
    ExpressionStatement,
    ForStatement,
    FunctionDeclaration,
    Grouping,
    Identifier,
    IfStatement,
    Literal,
    PrintStatement,
    Program,
    ReturnStatement,
    Statement,
    UnaryExpression,
    VariableDeclaration,
    WhileStatement,
)
from ..lexer.token_type import TokenType
from .symbol_table import Symbol, SymbolTable
from .types import TypeKind


class SemanticError(Exception):
    pass


@dataclass
class FunctionContext:
    name: str
    return_type: TypeKind = TypeKind.UNKNOWN
    has_return: bool = False


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.symbol_table = SymbolTable()
        self.errors: list[str] = []
        self.function_stack: list[FunctionContext] = []

    def analyze(self, program: Program) -> Program:
        self.errors = []
        self._predeclare(program)
        self.visit_program(program)
        if self.errors:
            raise SemanticError("\n".join(self.errors))
        return program

    def _predeclare(self, program: Program) -> None:
        for statement in program.statements:
            if isinstance(statement, FunctionDeclaration):
                try:
                    self.symbol_table.insert(
                        Symbol(
                            name=statement.name,
                            type=TypeKind.FUNCTION,
                            scope=self.symbol_table.current_scope.name,
                            params=[TypeKind.ANY for _ in statement.params],
                            return_type=TypeKind.UNKNOWN,
                        )
                    )
                except ValueError as error:
                    self.errors.append(str(error))

    def visit_program(self, program: Program) -> None:
        for statement in program.statements:
            self.visit_statement(statement)

    def visit_statement(self, statement: Statement) -> None:
        if isinstance(statement, Block):
            self.symbol_table.push_scope("block")
            for nested in statement.statements:
                self.visit_statement(nested)
            self.symbol_table.pop_scope()
            return
        if isinstance(statement, VariableDeclaration):
            self.visit_variable_declaration(statement)
            return
        if isinstance(statement, FunctionDeclaration):
            self.visit_function_declaration(statement)
            return
        if isinstance(statement, IfStatement):
            self.ensure_booleanish(self.visit_expression(statement.condition), "if condition")
            self.visit_statement(statement.then_branch)
            if statement.else_branch is not None:
                self.visit_statement(statement.else_branch)
            return
        if isinstance(statement, WhileStatement):
            self.ensure_booleanish(self.visit_expression(statement.condition), "while condition")
            self.visit_statement(statement.body)
            return
        if isinstance(statement, ForStatement):
            self.symbol_table.push_scope("for")
            if statement.initializer is not None:
                self.visit_statement(statement.initializer)
            if statement.condition is not None:
                self.ensure_booleanish(self.visit_expression(statement.condition), "for condition")
            if statement.increment is not None:
                self.visit_expression(statement.increment)
            self.visit_statement(statement.body)
            self.symbol_table.pop_scope()
            return
        if isinstance(statement, ReturnStatement):
            self.visit_return(statement)
            return
        if isinstance(statement, PrintStatement):
            if statement.value is not None:
                self.visit_expression(statement.value)
            return
        if isinstance(statement, ExpressionStatement):
            if statement.expression is not None:
                self.visit_expression(statement.expression)
            return
        self.errors.append(f"Unsupported statement {type(statement).__name__}")

    def visit_variable_declaration(self, statement: VariableDeclaration) -> None:
        inferred = TypeKind.ANY
        if statement.initializer is not None:
            inferred = self.visit_expression(statement.initializer)
        try:
            self.symbol_table.insert(Symbol(name=statement.name, type=inferred, scope=self.symbol_table.current_scope.name))
        except ValueError as error:
            self.errors.append(str(error))

    def visit_function_declaration(self, statement: FunctionDeclaration) -> None:
        function_symbol = self.symbol_table.lookup(statement.name)
        if function_symbol is None:
            self.errors.append(f"Undefined function {statement.name}")
            return
        self.symbol_table.push_scope(f"fn {statement.name}")
        for parameter in statement.params:
            try:
                self.symbol_table.insert(Symbol(name=parameter, type=TypeKind.ANY, scope=self.symbol_table.current_scope.name))
            except ValueError as error:
                self.errors.append(str(error))
        self.function_stack.append(FunctionContext(name=statement.name))
        self.visit_statement(statement.body)
        context = self.function_stack.pop()
        self.symbol_table.pop_scope()
        if context.has_return and function_symbol is not None and context.return_type is not TypeKind.UNKNOWN:
            function_symbol.return_type = context.return_type

    def visit_return(self, statement: ReturnStatement) -> None:
        if not self.function_stack:
            self.errors.append("Return outside of function")
            return
        return_type = TypeKind.NIL
        if statement.value is not None:
            return_type = self.visit_expression(statement.value)
        context = self.function_stack[-1]
        context.has_return = True
        if context.return_type in {TypeKind.UNKNOWN, TypeKind.NIL, TypeKind.ANY}:
            context.return_type = return_type
        elif context.return_type != return_type and return_type is not TypeKind.ANY:
            self.errors.append(f"Return type mismatch in {context.name}")

    def visit_expression(self, expression: Expression | None) -> TypeKind:
        if expression is None:
            return TypeKind.NIL
        if isinstance(expression, Literal):
            return self.literal_type(expression.value)
        if isinstance(expression, Identifier):
            symbol = self.symbol_table.lookup(expression.name)
            if symbol is None:
                self.errors.append(f"Undefined variable {expression.name}")
                return TypeKind.UNKNOWN
            return symbol.type
        if isinstance(expression, Grouping):
            return self.visit_expression(expression.expression)
        if isinstance(expression, Assignment):
            symbol = self.symbol_table.lookup(expression.target)
            if symbol is None:
                self.errors.append(f"Undefined variable {expression.target}")
                return TypeKind.UNKNOWN
            value_type = self.visit_expression(expression.value)
            if symbol.type is TypeKind.ANY:
                symbol.type = value_type
            elif value_type is not TypeKind.ANY and symbol.type != value_type:
                self.errors.append(f"Type mismatch assigning to {expression.target}")
            return symbol.type
        if isinstance(expression, UnaryExpression):
            operand_type = self.visit_expression(expression.operand)
            if expression.operator.type is TokenType.BANG:
                return TypeKind.BOOLEAN
            self.ensure_numeric(operand_type, "unary -")
            return operand_type
        if isinstance(expression, BinaryExpression):
            left_type = self.visit_expression(expression.left)
            right_type = self.visit_expression(expression.right)
            operator = expression.operator.type
            if operator in {TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT}:
                if operator is TokenType.PLUS and (left_type is TypeKind.STRING or right_type is TypeKind.STRING):
                    return TypeKind.STRING
                self.ensure_numeric(left_type, expression.operator.lexeme)
                self.ensure_numeric(right_type, expression.operator.lexeme)
                return TypeKind.FLOAT if TypeKind.FLOAT in {left_type, right_type} else TypeKind.INTEGER
            if operator in {TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL}:
                return TypeKind.BOOLEAN
            if operator in {TokenType.AND, TokenType.OR}:
                self.ensure_booleanish(left_type, expression.operator.lexeme)
                self.ensure_booleanish(right_type, expression.operator.lexeme)
                return TypeKind.BOOLEAN
            return TypeKind.UNKNOWN
        if isinstance(expression, CallExpression):
            return self.visit_call(expression)
        self.errors.append(f"Unsupported expression {type(expression).__name__}")
        return TypeKind.UNKNOWN

    def visit_call(self, expression: CallExpression) -> TypeKind:
        if isinstance(expression.callee, Identifier):
            symbol = self.symbol_table.lookup(expression.callee.name)
            if symbol is None:
                self.errors.append(f"Undefined function {expression.callee.name}")
                return TypeKind.UNKNOWN
            if symbol.type is not TypeKind.FUNCTION:
                self.errors.append(f"{expression.callee.name} is not callable")
                return TypeKind.UNKNOWN
            if symbol.params and len(symbol.params) != len(expression.arguments):
                self.errors.append(f"Argument count mismatch for {expression.callee.name}")
            for argument in expression.arguments:
                self.visit_expression(argument)
            return symbol.return_type if symbol.return_type is not TypeKind.UNKNOWN else TypeKind.ANY
        self.visit_expression(expression.callee)
        for argument in expression.arguments:
            self.visit_expression(argument)
        return TypeKind.ANY

    def literal_type(self, value: object) -> TypeKind:
        if value is None:
            return TypeKind.NIL
        if isinstance(value, bool):
            return TypeKind.BOOLEAN
        if isinstance(value, int):
            return TypeKind.INTEGER
        if isinstance(value, float):
            return TypeKind.FLOAT
        if isinstance(value, str):
            return TypeKind.STRING
        return TypeKind.ANY

    def ensure_numeric(self, type_kind: TypeKind, context: str) -> None:
        if type_kind not in {TypeKind.INTEGER, TypeKind.FLOAT, TypeKind.ANY, TypeKind.UNKNOWN}:
            self.errors.append(f"Expected numeric value in {context}")

    def ensure_booleanish(self, type_kind: TypeKind, context: str) -> None:
        if type_kind not in {TypeKind.BOOLEAN, TypeKind.INTEGER, TypeKind.FLOAT, TypeKind.ANY, TypeKind.UNKNOWN}:
            self.errors.append(f"Expected boolean value in {context}")
