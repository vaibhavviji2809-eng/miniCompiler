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
from .ir_instruction import IRFunction, IRInstruction, IRProgram


@dataclass
class BuildContext:
    name: str
    label_counter: int = 0


class IRBuilder:
    def build(self, program: Program) -> IRProgram:
        self.program_functions: dict[str, IRFunction] = {}
        main = IRFunction(name="main")
        self._compile_statements(program.statements, main, BuildContext("main"))
        if not main.instructions or main.instructions[-1].opcode != "RETURN":
            main.instructions.append(IRInstruction("LOAD_CONST", (None,)))
            main.instructions.append(IRInstruction("RETURN"))
        return IRProgram(main=main, functions=self.program_functions)

    def _compile_statements(self, statements: list[Statement], function: IRFunction, context: BuildContext) -> None:
        for statement in statements:
            self._compile_statement(statement, function, context)

    def _compile_statement(self, statement: Statement, function: IRFunction, context: BuildContext) -> None:
        if isinstance(statement, Block):
            self._compile_statements(statement.statements, function, context)
            return
        if isinstance(statement, VariableDeclaration):
            if statement.initializer is not None:
                self._compile_expression(statement.initializer, function, context)
            else:
                function.instructions.append(IRInstruction("LOAD_CONST", (None,)))
            function.instructions.append(IRInstruction("STORE_NAME", (statement.name,)))
            return
        if isinstance(statement, FunctionDeclaration):
            self.program_functions[statement.name] = self._compile_function(statement)
            return
        if isinstance(statement, StructDeclaration):
            return
        if isinstance(statement, IfStatement):
            self._compile_if(statement, function, context)
            return
        if isinstance(statement, WhileStatement):
            self._compile_while(statement, function, context)
            return
        if isinstance(statement, ForStatement):
            self._compile_for(statement, function, context)
            return
        if isinstance(statement, ReturnStatement):
            if statement.value is not None:
                self._compile_expression(statement.value, function, context)
            else:
                function.instructions.append(IRInstruction("LOAD_CONST", (None,)))
            function.instructions.append(IRInstruction("RETURN"))
            return
        if isinstance(statement, PrintStatement):
            if statement.value is not None:
                self._compile_expression(statement.value, function, context)
            else:
                function.instructions.append(IRInstruction("LOAD_CONST", (None,)))
            function.instructions.append(IRInstruction("PRINT"))
            return
        if isinstance(statement, ExpressionStatement):
            if statement.expression is not None:
                self._compile_expression(statement.expression, function, context)
                function.instructions.append(IRInstruction("POP"))
            return
        raise TypeError(f"Unsupported statement {type(statement).__name__}")

    def _compile_function(self, statement: FunctionDeclaration) -> IRFunction:
        context = BuildContext(name=statement.name)
        function = IRFunction(name=statement.name, params=statement.params.copy())
        self._compile_statements(statement.body.statements, function, context)
        if not function.instructions or function.instructions[-1].opcode != "RETURN":
            function.instructions.append(IRInstruction("LOAD_CONST", (None,)))
            function.instructions.append(IRInstruction("RETURN"))
        return function

    def _compile_if(self, statement: IfStatement, function: IRFunction, context: BuildContext) -> None:
        else_label = self._label(context, "else")
        end_label = self._label(context, "endif")
        self._compile_expression(statement.condition, function, context)
        function.instructions.append(IRInstruction("JUMP_IF_FALSE", (else_label,)))
        self._compile_statement(statement.then_branch, function, context)
        function.instructions.append(IRInstruction("JUMP", (end_label,)))
        function.instructions.append(IRInstruction("LABEL", (else_label,)))
        if statement.else_branch is not None:
            self._compile_statement(statement.else_branch, function, context)
        function.instructions.append(IRInstruction("LABEL", (end_label,)))

    def _compile_while(self, statement: WhileStatement, function: IRFunction, context: BuildContext) -> None:
        start_label = self._label(context, "while_start")
        end_label = self._label(context, "while_end")
        function.instructions.append(IRInstruction("LABEL", (start_label,)))
        self._compile_expression(statement.condition, function, context)
        function.instructions.append(IRInstruction("JUMP_IF_FALSE", (end_label,)))
        self._compile_statement(statement.body, function, context)
        function.instructions.append(IRInstruction("JUMP", (start_label,)))
        function.instructions.append(IRInstruction("LABEL", (end_label,)))

    def _compile_for(self, statement: ForStatement, function: IRFunction, context: BuildContext) -> None:
        if statement.initializer is not None:
            self._compile_statement(statement.initializer, function, context)
        start_label = self._label(context, "for_start")
        end_label = self._label(context, "for_end")
        function.instructions.append(IRInstruction("LABEL", (start_label,)))
        if statement.condition is not None:
            self._compile_expression(statement.condition, function, context)
        else:
            function.instructions.append(IRInstruction("LOAD_CONST", (True,)))
        function.instructions.append(IRInstruction("JUMP_IF_FALSE", (end_label,)))
        self._compile_statement(statement.body, function, context)
        if statement.increment is not None:
            self._compile_expression(statement.increment, function, context)
            function.instructions.append(IRInstruction("POP"))
        function.instructions.append(IRInstruction("JUMP", (start_label,)))
        function.instructions.append(IRInstruction("LABEL", (end_label,)))

    def _compile_expression(self, expression: Expression, function: IRFunction, context: BuildContext) -> None:
        if isinstance(expression, Literal):
            function.instructions.append(IRInstruction("LOAD_CONST", (expression.value,)))
            return
        if isinstance(expression, Identifier):
            function.instructions.append(IRInstruction("LOAD_NAME", (expression.name,)))
            return
        if isinstance(expression, Grouping):
            self._compile_expression(expression.expression, function, context)
            return
        if isinstance(expression, ArrayLiteral):
            for element in expression.elements:
                self._compile_expression(element, function, context)
            function.instructions.append(IRInstruction("BUILD_ARRAY", (len(expression.elements),)))
            return
        if isinstance(expression, StructLiteral):
            for _, value in expression.fields:
                self._compile_expression(value, function, context)
            field_names = tuple(name for name, _ in expression.fields)
            function.instructions.append(IRInstruction("BUILD_STRUCT", (expression.name, field_names, len(expression.fields))))
            return
        if isinstance(expression, Assignment):
            self._compile_expression(expression.value, function, context)
            function.instructions.append(IRInstruction("STORE_NAME", (expression.target,)))
            function.instructions.append(IRInstruction("LOAD_NAME", (expression.target,)))
            return
        if isinstance(expression, IndexExpression):
            self._compile_expression(expression.target, function, context)
            self._compile_expression(expression.index, function, context)
            function.instructions.append(IRInstruction("LOAD_INDEX"))
            return
        if isinstance(expression, MemberExpression):
            self._compile_expression(expression.target, function, context)
            function.instructions.append(IRInstruction("LOAD_MEMBER", (expression.member,)))
            return
        if isinstance(expression, UnaryExpression):
            self._compile_expression(expression.operand, function, context)
            opcode = "UNARY_NOT" if expression.operator.type is TokenType.BANG else "UNARY_NEG"
            function.instructions.append(IRInstruction(opcode))
            return
        if isinstance(expression, BinaryExpression):
            self._compile_expression(expression.left, function, context)
            self._compile_expression(expression.right, function, context)
            opcode = self._binary_opcode(expression.operator.type)
            function.instructions.append(IRInstruction(opcode))
            return
        if isinstance(expression, CallExpression):
            for argument in expression.arguments:
                self._compile_expression(argument, function, context)
            if isinstance(expression.callee, Identifier):
                function.instructions.append(IRInstruction("CALL", (expression.callee.name, len(expression.arguments))))
                return
            self._compile_expression(expression.callee, function, context)
            function.instructions.append(IRInstruction("CALL_DYNAMIC", (len(expression.arguments),)))
            return
        raise TypeError(f"Unsupported expression {type(expression).__name__}")

    def _binary_opcode(self, token_type: TokenType) -> str:
        return {
            TokenType.PLUS: "BINARY_ADD",
            TokenType.MINUS: "BINARY_SUB",
            TokenType.STAR: "BINARY_MUL",
            TokenType.SLASH: "BINARY_DIV",
            TokenType.PERCENT: "BINARY_MOD",
            TokenType.EQUAL_EQUAL: "COMPARE_EQ",
            TokenType.BANG_EQUAL: "COMPARE_NE",
            TokenType.GREATER: "COMPARE_GT",
            TokenType.GREATER_EQUAL: "COMPARE_GTE",
            TokenType.LESS: "COMPARE_LT",
            TokenType.LESS_EQUAL: "COMPARE_LTE",
            TokenType.AND: "BINARY_AND",
            TokenType.OR: "BINARY_OR",
        }[token_type]

    def _label(self, context: BuildContext, prefix: str) -> str:
        context.label_counter += 1
        return f"{context.name}_{prefix}_{context.label_counter}"
