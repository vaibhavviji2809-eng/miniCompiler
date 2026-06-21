# JIT Compilation

MiniCompiler includes an experimental JIT-style backend that lowers optimized IR to a register-machine program.

It supports:

- source -> IR -> machine code lowering
- function calls and recursion
- arrays and struct values
- execution via a dedicated machine runtime

Use `mc jit program.mc` to execute through this path.

