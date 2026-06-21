from __future__ import annotations

from .ir_instruction import IRFunction, IRProgram
from .passes import (
    common_subexpression_elimination,
    constant_folding,
    constant_propagation,
    copy_propagation,
    dead_code_elimination,
    strength_reduction,
)


def optimize_function(function: IRFunction) -> IRFunction:
    instructions = function.instructions
    instructions = copy_propagation(instructions)
    instructions = constant_propagation(instructions)
    instructions = constant_folding(instructions)
    instructions = strength_reduction(instructions)
    instructions = common_subexpression_elimination(instructions)
    instructions = dead_code_elimination(instructions)
    return IRFunction(name=function.name, params=function.params.copy(), instructions=instructions)


def optimize_program(program: IRProgram) -> IRProgram:
    optimized_main = optimize_function(program.main)
    optimized_functions = {name: optimize_function(function) for name, function in program.functions.items()}
    return IRProgram(main=optimized_main, functions=optimized_functions)
