from __future__ import annotations

import argparse
import copy
import sys
from dataclasses import is_dataclass, fields
from pathlib import Path
from typing import Any

from .bytecode.compiler import compile_ir_to_bytecode
from .ir.ir_builder import IRBuilder
from .ir.optimizer import optimize_program
from .parser.ast_nodes import (
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
from .parser.parser import Parser
from .semantic.analyzer import SemanticAnalyzer, SemanticError
from .semantic.symbol_table import Symbol
from .semantic.types import TypeKind
from .vm.vm import VirtualMachine


def load_source(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def compile_source(source: str) -> tuple[Program, object, object]:
    program = Parser(source).parse()
    semantic = SemanticAnalyzer()
    semantic.analyze(program)
    ir_program = IRBuilder().build(program)
    optimized_program = optimize_program(ir_program)
    bytecode_program = compile_ir_to_bytecode(optimized_program)
    return program, optimized_program, bytecode_program


def format_ast(node: Any, indent: int = 0) -> str:
    prefix = "  " * indent
    if isinstance(node, list):
        return "\n".join(format_ast(item, indent) for item in node)
    if not is_dataclass(node):
        return f"{prefix}{node!r}"
    label = type(node).__name__
    details: list[str] = []
    for field in fields(node):
        if field.name in {"line", "column"}:
            continue
        value = getattr(node, field.name)
        if isinstance(value, (Literal, Identifier, UnaryExpression, BinaryExpression, CallExpression, Grouping, Assignment, ExpressionStatement, VariableDeclaration, PrintStatement, ReturnStatement, IfStatement, WhileStatement, ForStatement, Block, FunctionDeclaration, Program)):
            details.append(f"{field.name}:\n{format_ast(value, indent + 1)}")
        elif isinstance(value, list):
            if value and any(is_dataclass(item) for item in value):
                nested = "\n".join(format_ast(item, indent + 2) for item in value)
                details.append(f"{field.name}:\n{nested}")
            else:
                details.append(f"{field.name}: {value!r}")
        else:
            details.append(f"{field.name}: {value!r}")
    if not details:
        return f"{prefix}{label}"
    joined = "\n".join(f"{prefix}  {detail}" for detail in details)
    return f"{prefix}{label}\n{joined}"


def format_ir(program: object) -> str:
    lines: list[str] = []
    for function in [program.main, *program.functions.values()]:
        lines.append(f"function {function.name}({', '.join(function.params)})")
        for instruction in function.instructions:
            operands = ", ".join(repr(operand) for operand in instruction.operands)
            lines.append(f"  {instruction.opcode} {operands}".rstrip())
    return "\n".join(lines)


def format_bytecode(program: object) -> str:
    lines: list[str] = []
    for function in [program.main, *program.functions.values()]:
        lines.append(f"function {function.name}({', '.join(function.params)})")
        for index, instruction in enumerate(function.instructions):
            operands = ", ".join(repr(operand) for operand in instruction.operands)
            lines.append(f"  {index:04d}: {instruction.opcode.value} {operands}".rstrip())
    return "\n".join(lines)


def execute_source(source: str, session: dict[str, Any] | None = None) -> tuple[object | None, Program, object, object]:
    program = Parser(source).parse()
    analyzer = SemanticAnalyzer()
    if session is not None:
        for symbol in session.get("symbols", {}).values():
            analyzer.symbol_table.insert(copy.deepcopy(symbol))
    analyzer.analyze(program)
    ir_program = optimize_program(IRBuilder().build(program))
    bytecode_program = compile_ir_to_bytecode(ir_program)
    vm = VirtualMachine(bytecode_program)
    if session is not None:
        vm.runtime.globals.update(session.get("globals", {}))
        vm.runtime.program.functions.update(session.get("functions", {}))
    result = vm.run()
    if session is not None:
        session.setdefault("globals", {}).update(vm.runtime.globals)
        session.setdefault("functions", {}).update(bytecode_program.functions)
        session.setdefault("symbols", {})
        for statement in program.statements:
            if isinstance(statement, VariableDeclaration):
                symbol = analyzer.symbol_table.lookup(statement.name)
                if symbol is not None:
                    session["symbols"][statement.name] = copy.deepcopy(symbol)
            if isinstance(statement, FunctionDeclaration):
                symbol = analyzer.symbol_table.lookup(statement.name)
                if symbol is not None:
                    session["symbols"][statement.name] = copy.deepcopy(symbol)
    return result, program, ir_program, bytecode_program


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mc", description="MiniCompiler toolchain")
    subcommands = parser.add_subparsers(dest="command", required=True)

    for command in ["build", "compile", "run", "ast", "ir", "bytecode", "repl"]:
        subcommands.add_parser(command).add_argument("source", nargs="?")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "repl":
        return repl()

    if not args.source:
        raise SystemExit("A source file path is required")

    source = load_source(args.source)
    ast_program, ir_program, bytecode_program = compile_source(source)

    if args.command == "ast":
        print(format_ast(ast_program))
        return 0
    if args.command == "ir":
        print(format_ir(ir_program))
        return 0
    if args.command == "bytecode":
        print(format_bytecode(bytecode_program))
        return 0
    if args.command in {"build", "compile"}:
        print(format_bytecode(bytecode_program))
        return 0
    if args.command == "run":
        vm = VirtualMachine(bytecode_program)
        value = vm.run()
        if vm.outputs:
            for item in vm.outputs:
                print(item)
        elif value is not None:
            print(value)
        return 0
    return 0


def repl() -> int:
    session: dict[str, Any] = {"globals": {}, "functions": {}, "symbols": {}}
    while True:
        try:
            source = input("mc> ").strip()
        except EOFError:
            break
        if not source:
            continue
        if source in {"exit", "quit"}:
            break
        if not source.endswith((";", "}", ")")) and not source.startswith(("fn ", "if ", "while ", "for ", "let ", "return ", "print(")):
            source = f"{source};"
        try:
            result, _, _, _ = execute_source(source, session)
            if result is not None and not source.startswith("print"):
                print(result)
        except (SemanticError, Exception) as error:
            print(error)
    return 0
