from __future__ import annotations

from .bytecode import BytecodeFunction, BytecodeProgram, Instruction
from .opcode import Opcode
from ..ir.ir_instruction import IRFunction, IRInstruction, IRProgram


def compile_ir_to_bytecode(program: IRProgram) -> BytecodeProgram:
    main = compile_function(program.main)
    functions = {name: compile_function(function) for name, function in program.functions.items()}
    return BytecodeProgram(main=main, functions=functions)


def compile_function(function: IRFunction) -> BytecodeFunction:
    label_map = build_label_map(function.instructions)
    instructions: list[Instruction] = []
    for instruction in function.instructions:
        if instruction.opcode == "LABEL":
            continue
        operands = tuple(resolve_operand(operand, label_map) for operand in instruction.operands)
        instructions.append(Instruction(Opcode[instruction.opcode], operands))
    return BytecodeFunction(name=function.name, params=function.params.copy(), instructions=instructions)


def build_label_map(instructions: list[IRInstruction]) -> dict[str, int]:
    label_map: dict[str, int] = {}
    address = 0
    for instruction in instructions:
        if instruction.opcode == "LABEL":
            label_map[instruction.operands[0]] = address
        else:
            address += 1
    return label_map


def resolve_operand(operand: object, label_map: dict[str, int]) -> object:
    if isinstance(operand, str) and operand in label_map:
        return label_map[operand]
    return operand

