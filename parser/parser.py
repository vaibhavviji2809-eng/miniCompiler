from __future__ import annotations

from typing import Optional

from ..lexer.lexer import Lexer, LexerError
from ..lexer.token import Token
from ..lexer.token_type import TokenType
from .ast_nodes import (
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


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, source: str | list[Token]) -> None:
        if isinstance(source, str):
            try:
                self.tokens = Lexer(source).tokenize()
            except LexerError as error:
                raise ParseError(str(error)) from error
        else:
            self.tokens = source
        self.current = 0

    def parse(self) -> Program:
        return self.parse_program()

    def parse_program(self) -> Program:
        statements: list[Statement] = []
        while not self.is_at_end():
            statements.append(self.parse_statement())
        return Program(statements=statements)

    def parse_statement(self) -> Statement:
        if self.match(TokenType.LET):
            return self.parse_variable_declaration()
        if self.match(TokenType.FN):
            return self.parse_function()
        if self.match(TokenType.IF):
            return self.parse_if()
        if self.match(TokenType.WHILE):
            return self.parse_while()
        if self.match(TokenType.FOR):
            return self.parse_for()
        if self.match(TokenType.RETURN):
            return self.parse_return()
        if self.match(TokenType.PRINT):
            return self.parse_print()
        if self.match(TokenType.LEFT_BRACE):
            return self.parse_block()
        expression = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after expression")
        return ExpressionStatement(expression=expression, line=expression.line, column=expression.column)

    def parse_block(self) -> Block:
        statements: list[Statement] = []
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            statements.append(self.parse_statement())
        self.consume(TokenType.RIGHT_BRACE, "Expected '}' after block")
        return Block(statements=statements)

    def parse_variable_declaration(self) -> VariableDeclaration:
        name = self.consume(TokenType.IDENTIFIER, "Expected variable name")
        initializer: Optional[Expression] = None
        if self.match(TokenType.EQUAL):
            initializer = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VariableDeclaration(name=name.lexeme, initializer=initializer, line=name.line, column=name.column)

    def parse_function(self) -> FunctionDeclaration:
        name = self.consume(TokenType.IDENTIFIER, "Expected function name")
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after function name")
        params: list[str] = []
        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                parameter = self.consume(TokenType.IDENTIFIER, "Expected parameter name")
                params.append(parameter.lexeme)
                if not self.match(TokenType.COMMA):
                    break
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters")
        self.consume(TokenType.LEFT_BRACE, "Expected '{' before function body")
        body = self.parse_block()
        return FunctionDeclaration(name=name.lexeme, params=params, body=body, line=name.line, column=name.column)

    def parse_if(self) -> IfStatement:
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after if")
        condition = self.parse_expression()
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after if condition")
        self.consume(TokenType.LEFT_BRACE, "Expected '{' after if condition")
        then_branch = self.parse_block()
        else_branch = None
        if self.match(TokenType.ELSE):
            self.consume(TokenType.LEFT_BRACE, "Expected '{' after else")
            else_branch = self.parse_block()
        return IfStatement(condition=condition, then_branch=then_branch, else_branch=else_branch, line=condition.line, column=condition.column)

    def parse_while(self) -> WhileStatement:
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after while")
        condition = self.parse_expression()
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after while condition")
        self.consume(TokenType.LEFT_BRACE, "Expected '{' after while condition")
        body = self.parse_block()
        return WhileStatement(condition=condition, body=body, line=condition.line, column=condition.column)

    def parse_for(self) -> ForStatement:
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after for")
        initializer: Optional[Statement] = None
        if not self.check(TokenType.SEMICOLON):
            if self.match(TokenType.LET):
                initializer = self.parse_variable_declaration()
            else:
                expression = self.parse_expression()
                self.consume(TokenType.SEMICOLON, "Expected ';' after for initializer")
                initializer = ExpressionStatement(expression=expression, line=expression.line, column=expression.column)
        else:
            self.advance()
        condition: Optional[Expression] = None
        if not self.check(TokenType.SEMICOLON):
            condition = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after for condition")
        increment: Optional[Expression] = None
        if not self.check(TokenType.RIGHT_PAREN):
            increment = self.parse_expression()
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after for clauses")
        self.consume(TokenType.LEFT_BRACE, "Expected '{' after for clauses")
        body = self.parse_block()
        return ForStatement(initializer=initializer, condition=condition, increment=increment, body=body)

    def parse_return(self) -> ReturnStatement:
        keyword = self.previous()
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after return value")
        return ReturnStatement(value=value, line=keyword.line, column=keyword.column)

    def parse_print(self) -> PrintStatement:
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after print")
        value = self.parse_expression()
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after print argument")
        self.consume(TokenType.SEMICOLON, "Expected ';' after print statement")
        return PrintStatement(value=value, line=value.line, column=value.column)

    def parse_expression(self) -> Expression:
        return self.parse_assignment()

    def parse_assignment(self) -> Expression:
        expression = self.parse_or()
        if self.match(TokenType.EQUAL):
            equals = self.previous()
            value = self.parse_assignment()
            if isinstance(expression, Identifier):
                return Assignment(target=expression.name, value=value, line=equals.line, column=equals.column)
            raise ParseError("Invalid assignment target")
        return expression

    def parse_or(self) -> Expression:
        expression = self.parse_and()
        while self.match(TokenType.OR):
            operator = self.previous()
            right = self.parse_and()
            expression = BinaryExpression(left=expression, operator=operator, right=right, line=operator.line, column=operator.column)
        return expression

    def parse_and(self) -> Expression:
        expression = self.parse_equality()
        while self.match(TokenType.AND):
            operator = self.previous()
            right = self.parse_equality()
            expression = BinaryExpression(left=expression, operator=operator, right=right, line=operator.line, column=operator.column)
        return expression

    def parse_equality(self) -> Expression:
        return self.parse_binary(self.parse_comparison, {TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL})

    def parse_comparison(self) -> Expression:
        return self.parse_binary(self.parse_term, {TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL})

    def parse_term(self) -> Expression:
        return self.parse_binary(self.parse_factor, {TokenType.PLUS, TokenType.MINUS})

    def parse_factor(self) -> Expression:
        return self.parse_binary(self.parse_unary, {TokenType.STAR, TokenType.SLASH, TokenType.PERCENT})

    def parse_binary(self, lower_parser, operators: set[TokenType]) -> Expression:
        expression = lower_parser()
        while self.match(*operators):
            operator = self.previous()
            right = lower_parser()
            expression = BinaryExpression(left=expression, operator=operator, right=right, line=operator.line, column=operator.column)
        return expression

    def parse_unary(self) -> Expression:
        if self.match(TokenType.BANG, TokenType.MINUS):
            operator = self.previous()
            operand = self.parse_unary()
            return UnaryExpression(operator=operator, operand=operand, line=operator.line, column=operator.column)
        return self.parse_call()

    def parse_call(self) -> Expression:
        expression = self.parse_primary()
        while self.match(TokenType.LEFT_PAREN):
            arguments: list[Expression] = []
            if not self.check(TokenType.RIGHT_PAREN):
                while True:
                    arguments.append(self.parse_expression())
                    if not self.match(TokenType.COMMA):
                        break
            paren = self.consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments")
            expression = CallExpression(callee=expression, arguments=arguments, line=paren.line, column=paren.column)
        return expression

    def parse_primary(self) -> Expression:
        if self.match(TokenType.NUMBER):
            token = self.previous()
            return Literal(value=token.literal, line=token.line, column=token.column)
        if self.match(TokenType.STRING):
            token = self.previous()
            return Literal(value=token.literal, line=token.line, column=token.column)
        if self.match(TokenType.TRUE):
            token = self.previous()
            return Literal(value=True, line=token.line, column=token.column)
        if self.match(TokenType.FALSE):
            token = self.previous()
            return Literal(value=False, line=token.line, column=token.column)
        if self.match(TokenType.NIL):
            token = self.previous()
            return Literal(value=None, line=token.line, column=token.column)
        if self.match(TokenType.IDENTIFIER):
            token = self.previous()
            return Identifier(name=token.lexeme, line=token.line, column=token.column)
        if self.match(TokenType.LEFT_PAREN):
            expression = self.parse_expression()
            self.consume(TokenType.RIGHT_PAREN, "Expected ')' after expression")
            return Grouping(expression=expression, line=expression.line, column=expression.column)
        raise ParseError(f"Unexpected token {self.peek().type.name}")

    def match(self, *types: TokenType) -> bool:
        for token_type in types:
            if self.check(token_type):
                self.advance()
                return True
        return False

    def consume(self, token_type: TokenType, message: str) -> Token:
        if self.check(token_type):
            return self.advance()
        raise ParseError(message)

    def check(self, token_type: TokenType) -> bool:
        if self.is_at_end():
            return token_type is TokenType.EOF
        return self.peek().type is token_type

    def advance(self) -> Token:
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def is_at_end(self) -> bool:
        return self.peek().type is TokenType.EOF

    def peek(self) -> Token:
        return self.tokens[self.current]

    def previous(self) -> Token:
        return self.tokens[self.current - 1]

