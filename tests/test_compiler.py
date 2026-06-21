from __future__ import annotations

import unittest

from MiniCompiler.cli import compile_source, execute_source
from MiniCompiler.ir.control_flow import ControlFlowGraph, detect_loops
from MiniCompiler.ir.ir_builder import IRBuilder
from MiniCompiler.ir.optimizer import optimize_program
from MiniCompiler.ir.register_allocation import allocate_registers, live_variable_analysis
from MiniCompiler.ir.jit import JITCompiler, MachineRuntime
from MiniCompiler.lexer.lexer import Lexer
from MiniCompiler.lexer.token_type import TokenType
from MiniCompiler.parser.parser import Parser
from MiniCompiler.semantic.analyzer import SemanticAnalyzer, SemanticError


FIBONACCI_SOURCE = """
fn fibonacci(n) {
    if (n <= 1) {
        return n;
    }

    return fibonacci(n - 1) + fibonacci(n - 2);
}

print(fibonacci(10));
"""


class CompilerTests(unittest.TestCase):
    def test_lexer(self) -> None:
        tokens = Lexer("let x = 10 + 20;").tokenize()
        types = [token.type for token in tokens]
        self.assertEqual(
            types,
            [
                TokenType.LET,
                TokenType.IDENTIFIER,
                TokenType.EQUAL,
                TokenType.NUMBER,
                TokenType.PLUS,
                TokenType.NUMBER,
                TokenType.SEMICOLON,
                TokenType.EOF,
            ],
        )

    def test_parser_builds_ast(self) -> None:
        program = Parser("print(10 + 20);").parse()
        self.assertEqual(len(program.statements), 1)

    def test_semantic_error(self) -> None:
        program = Parser("x + 10;").parse()
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError):
            analyzer.analyze(program)

    def test_fibonacci_pipeline(self) -> None:
        result, program, ir_program, bytecode_program = execute_source(FIBONACCI_SOURCE)
        self.assertEqual(result, 55)
        self.assertEqual(program.statements[0].name, "fibonacci")
        self.assertGreater(len(ir_program.main.instructions), 0)
        self.assertGreater(len(bytecode_program.main.instructions), 0)

    def test_for_loop(self) -> None:
        source = """
        let sum = 0;
        for (let i = 0; i < 4; i = i + 1) {
            sum = sum + i;
        }
        print(sum);
        """
        result, _, _, _ = execute_source(source)
        self.assertEqual(result, 6)

    def test_arrays_and_structs(self) -> None:
        source = """
        struct Point { x: int, y: int }
        let values = [1, 2, 3];
        let point = Point { x: 7, y: 5 };
        print(values[1] + point.y);
        """
        result, _, _, _ = execute_source(source)
        self.assertEqual(result, 7)

    def test_cfg_and_loops(self) -> None:
        program = Parser(
            """
            let i = 0;
            while (i < 3) {
                i = i + 1;
            }
            """
        ).parse()
        ir_program = optimize_program(IRBuilder().build(program))
        cfg = ControlFlowGraph.from_function(ir_program.main)
        self.assertGreaterEqual(len(cfg.blocks), 1)
        self.assertTrue(detect_loops(cfg))

    def test_register_allocation(self) -> None:
        program = Parser("let x = 1; let y = x + 2; print(y);").parse()
        ir_program = optimize_program(IRBuilder().build(program))
        allocation = allocate_registers(ir_program.main)
        self.assertIn("x", allocation.interference_graph)
        self.assertGreaterEqual(len(allocation.register_map), 1)

    def test_jit_backend(self) -> None:
        program = Parser(FIBONACCI_SOURCE).parse()
        ir_program = optimize_program(IRBuilder().build(program))
        machine_program = JITCompiler().compile_program(ir_program)
        runtime = MachineRuntime(machine_program)
        result = runtime.run()
        self.assertEqual(result, 55)
        self.assertEqual(runtime.outputs[-1], 55)


if __name__ == "__main__":
    unittest.main()
