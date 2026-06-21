# MiniCompiler

MiniCompiler is a small end-to-end compiler pipeline for a toy language with:

- lexing and tokenization
- recursive descent parsing
- AST construction
- semantic analysis
- IR generation and optimization
- bytecode compilation
- a stack-based virtual machine
- a simple REPL and CLI

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

## CLI

- `python mc.py ast examples/fibonacci.mc`
- `python mc.py ir examples/fibonacci.mc`
- `python mc.py bytecode examples/fibonacci.mc`
- `python mc.py machinecode examples/fibonacci.mc`
- `python mc.py jit examples/fibonacci.mc`
- `python mc.py run examples/fibonacci.mc`
