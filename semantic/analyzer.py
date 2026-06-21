from __future__ import annotations

from dataclasses import dataclass

from ..lexer.token_type import TokenType
from ..parser.ast_nodes import (
    ArrayLiteral,
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
    IndexExpression,
    Literal,
    MemberExpression,
    PrintStatement,
    Program,
    ReturnStatement,
    Statement,
    StructDeclaration,
    StructLiteral,
    UnaryExpression,
    VariableDeclaration,
    WhileStatement,
)
from .symbol_table import Symbol, SymbolTable
from .types import (
    ANY_TYPE,
    BOOLEAN_TYPE,
    FLOAT_TYPE,
    INTEGER_TYPE,
    NIL_TYPE,
    STRING_TYPE,
    Type,
    TypeKind,
    UNKNOWN_TYPE,
    array_of,
    function_type,
    generic_type,
    struct_type,
)


class SemanticError(Exception):
    pass


@dataclass
class FunctionContext:
    name: str
    return_type: Type = UNKNOWN_TYPE
    has_return: bool = False


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.symbol_table = SymbolTable()
        self.errors: list[str] = []
        self.function_stack: list[FunctionContext] = []
        self.structs: dict[str, dict[str, Type]] = {}
        self.type_aliases: dict[str, Type] = {
            "any": ANY_TYPE,
            "unknown": UNKNOWN_TYPE,
            "nil": NIL_TYPE,
            "bool": BOOLEAN_TYPE,
            "boolean": BOOLEAN_TYPE,
            "int": INTEGER_TYPE,
            "integer": INTEGER_TYPE,
            "float": FLOAT_TYPE,
            "string": STRING_TYPE,
        }

    def analyze(self, program: Program) -> Program:
        self.errors = []
        self._predeclare(program)
        self.visit_program(program)
        if self.errors:
            raise SemanticError("\n".join(self.errors))
        return program

    def _predeclare(self, program: Program) -> None:
        for statement in program.statements:
            if isinstance(statement, StructDeclaration):
                fields = self.resolve_struct_fields(statement)
                self.structs[statement.name] = fields
                try:
                    self.symbol_table.insert(
                        Symbol(
                            name=statement.name,
                            type=struct_type(statement.name, fields),
                            scope=self.symbol_table.current_scope.name,
                        )
                    )
                except ValueError as error:
                    self.errors.append(str(error))
            if isinstance(statement, FunctionDeclaration):
                parameter_types = [ANY_TYPE for _ in statement.params]
                fn_type = function_type(parameter_types, UNKNOWN_TYPE)
                try:
                    self.symbol_table.insert(
                        Symbol(
                            name=statement.name,
                            type=fn_type,
                            scope=self.symbol_table.current_scope.name,
                            params=parameter_types,
                            return_type=UNKNOWN_TYPE,
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
        if isinstance(statement, StructDeclaration):
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
        inferred = self.type_from_annotation(statement.type_annotation) if statement.type_annotation is not None else ANY_TYPE
        if statement.initializer is not None:
            initializer_type = self.visit_expression(statement.initializer)
            inferred = self.unify(inferred, initializer_type)
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
                self.symbol_table.insert(Symbol(name=parameter, type=ANY_TYPE, scope=self.symbol_table.current_scope.name))
            except ValueError as error:
                self.errors.append(str(error))
        self.function_stack.append(FunctionContext(name=statement.name))
        self.visit_statement(statement.body)
        context = self.function_stack.pop()
        self.symbol_table.pop_scope()
        if context.has_return and context.return_type.kind is not TypeKind.UNKNOWN:
            function_symbol.return_type = context.return_type
            function_symbol.type = function_type(function_symbol.params, context.return_type)

    def visit_return(self, statement: ReturnStatement) -> None:
        if not self.function_stack:
            self.errors.append("Return outside of function")
            return
        return_type = NIL_TYPE
        if statement.value is not None:
            return_type = self.visit_expression(statement.value)
        context = self.function_stack[-1]
        context.has_return = True
        if context.return_type.kind in {TypeKind.UNKNOWN, TypeKind.NIL, TypeKind.ANY}:
            context.return_type = return_type
        elif not self.is_compatible(context.return_type, return_type):
            self.errors.append(f"Return type mismatch in {context.name}")

    def visit_expression(self, expression: Expression | None) -> Type:
        if expression is None:
            return NIL_TYPE
        if isinstance(expression, Literal):
            return self.literal_type(expression.value)
        if isinstance(expression, Identifier):
            symbol = self.symbol_table.lookup(expression.name)
            if symbol is None:
                self.errors.append(f"Undefined variable {expression.name}")
                return UNKNOWN_TYPE
            return symbol.type
        if isinstance(expression, Grouping):
            return self.visit_expression(expression.expression)
        if isinstance(expression, Assignment):
            symbol = self.symbol_table.lookup(expression.target)
            if symbol is None:
                self.errors.append(f"Undefined variable {expression.target}")
                return UNKNOWN_TYPE
            value_type = self.visit_expression(expression.value)
            if symbol.type.kind is TypeKind.ANY:
                symbol.type = value_type
            elif not self.is_compatible(symbol.type, value_type):
                self.errors.append(f"Type mismatch assigning to {expression.target}")
            return symbol.type
        if isinstance(expression, ArrayLiteral):
            element_type = ANY_TYPE
            for element in expression.elements:
                current_type = self.visit_expression(element)
                element_type = self.unify(element_type, current_type)
            return array_of(element_type)
        if isinstance(expression, IndexExpression):
            target_type = self.visit_expression(expression.target)
            self.ensure_indexable(target_type)
            index_type = self.visit_expression(expression.index)
            if index_type.kind not in {TypeKind.INTEGER, TypeKind.ANY, TypeKind.UNKNOWN}:
                self.errors.append("Array index must be an integer")
            if target_type.kind is TypeKind.ARRAY and target_type.element_type is not None:
                return target_type.element_type
            return ANY_TYPE
        if isinstance(expression, StructLiteral):
            struct_fields = self.structs.get(expression.name)
            if struct_fields is None:
                self.errors.append(f"Unknown struct {expression.name}")
                return UNKNOWN_TYPE
            provided = {name: self.visit_expression(value) for name, value in expression.fields}
            for field_name, field_type in struct_fields.items():
                if field_name not in provided:
                    self.errors.append(f"Missing field {field_name} in {expression.name}")
                    continue
                if not self.is_compatible(field_type, provided[field_name]):
                    self.errors.append(f"Type mismatch for field {field_name} in {expression.name}")
            return struct_type(expression.name, struct_fields)
        if isinstance(expression, MemberExpression):
            target_type = self.visit_expression(expression.target)
            if target_type.kind is TypeKind.STRUCT:
                fields = dict(target_type.fields)
                field_type = fields.get(expression.member)
                if field_type is None:
                    self.errors.append(f"Unknown field {expression.member} on {target_type.name}")
                    return UNKNOWN_TYPE
                return field_type
            self.errors.append("Member access requires a struct value")
            return UNKNOWN_TYPE
        if isinstance(expression, UnaryExpression):
            operand_type = self.visit_expression(expression.operand)
            if expression.operator.type is TokenType.BANG:
                return BOOLEAN_TYPE
            self.ensure_numeric(operand_type, "unary -")
            return operand_type
        if isinstance(expression, BinaryExpression):
            left_type = self.visit_expression(expression.left)
            right_type = self.visit_expression(expression.right)
            operator = expression.operator.type
            if operator in {TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT}:
                if operator is TokenType.PLUS and (left_type.kind is TypeKind.STRING or right_type.kind is TypeKind.STRING):
                    return STRING_TYPE
                self.ensure_numeric(left_type, expression.operator.lexeme)
                self.ensure_numeric(right_type, expression.operator.lexeme)
                return FLOAT_TYPE if TypeKind.FLOAT in {left_type.kind, right_type.kind} else INTEGER_TYPE
            if operator in {TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL}:
                return BOOLEAN_TYPE
            if operator in {TokenType.AND, TokenType.OR}:
                self.ensure_booleanish(left_type, expression.operator.lexeme)
                self.ensure_booleanish(right_type, expression.operator.lexeme)
                return BOOLEAN_TYPE
            return UNKNOWN_TYPE
        if isinstance(expression, CallExpression):
            return self.visit_call(expression)
        self.errors.append(f"Unsupported expression {type(expression).__name__}")
        return UNKNOWN_TYPE

    def visit_call(self, expression: CallExpression) -> Type:
        if isinstance(expression.callee, Identifier):
            symbol = self.symbol_table.lookup(expression.callee.name)
            if symbol is None:
                self.errors.append(f"Undefined function {expression.callee.name}")
                return UNKNOWN_TYPE
            if symbol.type.kind is not TypeKind.FUNCTION:
                self.errors.append(f"{expression.callee.name} is not callable")
                return UNKNOWN_TYPE
            if symbol.params and len(symbol.params) != len(expression.arguments):
                self.errors.append(f"Argument count mismatch for {expression.callee.name}")
            for index, argument in enumerate(expression.arguments):
                argument_type = self.visit_expression(argument)
                if index < len(symbol.params) and not self.is_compatible(symbol.params[index], argument_type):
                    self.errors.append(f"Argument type mismatch for {expression.callee.name}")
            return symbol.return_type
        self.visit_expression(expression.callee)
        for argument in expression.arguments:
            self.visit_expression(argument)
        return ANY_TYPE

    def literal_type(self, value: object) -> Type:
        if value is None:
            return NIL_TYPE
        if isinstance(value, bool):
            return BOOLEAN_TYPE
        if isinstance(value, int):
            return INTEGER_TYPE
        if isinstance(value, float):
            return FLOAT_TYPE
        if isinstance(value, str):
            return STRING_TYPE
        return ANY_TYPE

    def type_from_annotation(self, annotation: object) -> Type:
        if isinstance(annotation, Identifier):
            return self.type_aliases.get(annotation.name.lower(), self.struct_reference(annotation.name))
        if isinstance(annotation, ArrayLiteral) and len(annotation.elements) == 1:
            return array_of(self.visit_expression(annotation.elements[0]))
        return ANY_TYPE

    def struct_reference(self, name: str) -> Type:
        fields = self.structs.get(name)
        if fields is None:
            return generic_type(name)
        return struct_type(name, fields)

    def resolve_struct_fields(self, statement: StructDeclaration) -> dict[str, Type]:
        fields: dict[str, Type] = {}
        for field_name, field_type_expr in statement.fields:
            if field_type_expr is None:
                fields[field_name] = ANY_TYPE
            else:
                fields[field_name] = self.type_from_annotation(field_type_expr)
        return fields

    def unify(self, left: Type, right: Type) -> Type:
        if left.kind in {TypeKind.ANY, TypeKind.UNKNOWN}:
            return right
        if right.kind in {TypeKind.ANY, TypeKind.UNKNOWN}:
            return left
        if left.kind == right.kind:
            if left.kind is TypeKind.ARRAY and left.element_type and right.element_type:
                return array_of(self.unify(left.element_type, right.element_type))
            return left
        if {left.kind, right.kind} <= {TypeKind.INTEGER, TypeKind.FLOAT}:
            return FLOAT_TYPE
        return ANY_TYPE

    def is_compatible(self, expected: Type, actual: Type) -> bool:
        if expected.kind in {TypeKind.ANY, TypeKind.UNKNOWN} or actual.kind in {TypeKind.ANY, TypeKind.UNKNOWN}:
            return True
        if expected.kind != actual.kind:
            if {expected.kind, actual.kind} <= {TypeKind.INTEGER, TypeKind.FLOAT}:
                return True
            return False
        if expected.kind is TypeKind.ARRAY:
            if expected.element_type is None or actual.element_type is None:
                return True
            return self.is_compatible(expected.element_type, actual.element_type)
        if expected.kind is TypeKind.STRUCT:
            return expected.name == actual.name
        if expected.kind is TypeKind.FUNCTION:
            return len(expected.parameter_types) == len(actual.parameter_types)
        return True

    def ensure_numeric(self, type_kind: Type, context: str) -> None:
        if type_kind.kind not in {TypeKind.INTEGER, TypeKind.FLOAT, TypeKind.ANY, TypeKind.UNKNOWN}:
            self.errors.append(f"Expected numeric value in {context}")

    def ensure_booleanish(self, type_kind: Type, context: str) -> None:
        if type_kind.kind not in {TypeKind.BOOLEAN, TypeKind.INTEGER, TypeKind.FLOAT, TypeKind.ANY, TypeKind.UNKNOWN}:
            self.errors.append(f"Expected boolean value in {context}")

    def ensure_indexable(self, type_kind: Type) -> None:
        if type_kind.kind not in {TypeKind.ARRAY, TypeKind.ANY, TypeKind.UNKNOWN}:
            self.errors.append("Indexing requires an array")

