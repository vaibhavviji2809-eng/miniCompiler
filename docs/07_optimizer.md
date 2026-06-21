# Optimizer

The optimizer currently applies:

- constant propagation
- constant folding
- dead code elimination
- strength reduction
- a limited common subexpression elimination pass

These passes run before bytecode generation.

