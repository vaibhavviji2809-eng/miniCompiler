# Register Allocation

MiniCompiler includes a register-allocation analysis pipeline for IR values and locals.

Implemented pieces:

- live variable analysis
- interference graph construction
- graph coloring allocation
- spill slot assignment when registers run out

This is a backend analysis layer and does not replace the stack VM.

