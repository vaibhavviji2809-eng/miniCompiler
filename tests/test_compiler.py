from __future__ import annotations

import unittest

from MiniCompiler.cli import compile_source, execute_source
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


if __name__ == "__main__":
    unittest.main()

