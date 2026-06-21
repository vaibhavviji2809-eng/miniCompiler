# MiniCompiler

MiniCompiler is a small end-to-end compiler for a toy language, built to show the whole pipeline from source code to execution.

## What It Does

- Lexes source text into tokens
- Parses tokens into an AST
- Runs semantic analysis and type checks
- Lowers AST to IR
- Optimizes IR with compiler passes
- Compiles IR to bytecode or machine-code style instructions
- Executes programs on a stack VM or a register-machine JIT runtime

## Language Features

- Variables and assignment
- Functions and recursion
- Arithmetic and comparison
- Boolean logic
- `if` / `else`
- `while` and `for`
- `return`
- `print`
- Arrays
- Structs

## Example

```mc
fn fibonacci(n) {
    if (n <= 1) {
        return n;
    }

    return fibonacci(n - 1) + fibonacci(n - 2);
}

print(fibonacci(10));
```

## Quickstart

Run the sample program:

```bash
python outputs/MiniCompiler/mc.py run outputs/MiniCompiler/examples/fibonacci.mc
```

Explore the compilation stages:

```bash
python outputs/MiniCompiler/mc.py ast outputs/MiniCompiler/examples/fibonacci.mc
python outputs/MiniCompiler/mc.py ir outputs/MiniCompiler/examples/fibonacci.mc
python outputs/MiniCompiler/mc.py bytecode outputs/MiniCompiler/examples/fibonacci.mc
python outputs/MiniCompiler/mc.py machinecode outputs/MiniCompiler/examples/fibonacci.mc
python outputs/MiniCompiler/mc.py jit outputs/MiniCompiler/examples/fibonacci.mc
```

## Install

You can install the package locally with:

```bash
python -m pip install -e .
```

That gives you the `mc` entry point from `pyproject.toml`.

## Project Layout

- `lexer/` tokenization
- `parser/` AST and recursive descent parsing
- `semantic/` symbol tables and type checking
- `ir/` IR, optimization, CFG, register allocation, and JIT lowering
- `bytecode/` bytecode format and compiler
- `vm/` stack VM runtime
- `examples/` runnable sample programs
- `tests/` unit tests
- `docs/` phase-by-phase documentation

## Commands

- `mc build program.mc`
- `mc run program.mc`
- `mc compile program.mc`
- `mc ast program.mc`
- `mc ir program.mc`
- `mc bytecode program.mc`
- `mc machinecode program.mc`
- `mc jit program.mc`

## Output

Running the bundled fibonacci example prints:

```text
55
```
