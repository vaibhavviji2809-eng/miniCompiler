from .control_flow import BasicBlock, ControlFlowGraph, compute_dominators, detect_loops
from .jit import JITCompiler, MachineProgram, MachineRuntime
from .ir_builder import IRBuilder
from .ir_instruction import IRFunction, IRInstruction, IRProgram
from .register_allocation import allocate_registers, live_variable_analysis
from .optimizer import optimize_program
