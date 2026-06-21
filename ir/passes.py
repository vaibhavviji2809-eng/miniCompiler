from __future__ import annotations

from .control_flow import ControlFlowGraph
from .ir_instruction import IRInstruction


PURE_BINARY_OPS = {
    "BINARY_ADD",
    "BINARY_SUB",
    "BINARY_MUL",
    "BINARY_DIV",
    "BINARY_MOD",
    "BINARY_SHL",
    "BINARY_AND",
    "BINARY_OR",
    "COMPARE_EQ",
    "COMPARE_NE",
    "COMPARE_LT",
    "COMPARE_LTE",
    "COMPARE_GT",
    "COMPARE_GTE",
}

PURE_UNARY_OPS = {"UNARY_NEG", "UNARY_NOT"}


def copy_propagation(instructions: list[IRInstruction]) -> list[IRInstruction]:
    aliases: dict[str, str] = {}
    propagated: list[IRInstruction] = []
    for instruction in instructions:
        opcode = instruction.opcode
        if opcode == "LOAD_NAME":
            name = instruction.operands[0]
            while name in aliases and aliases[name] != name:
                name = aliases[name]
            propagated.append(IRInstruction("LOAD_NAME", (name,)))
            continue
        if opcode == "STORE_NAME" and propagated:
            source = propagated[-1]
            destination = instruction.operands[0]
            if source.opcode == "LOAD_NAME":
                aliases[destination] = source.operands[0]
            else:
                aliases.pop(destination, None)
            propagated.append(instruction)
            continue
        if opcode in {"CALL", "CALL_DYNAMIC", "RETURN", "JUMP", "JUMP_IF_FALSE", "LABEL", "PRINT"}:
            aliases.clear()
        propagated.append(instruction)
    return propagated


def constant_propagation(instructions: list[IRInstruction]) -> list[IRInstruction]:
    constants: dict[str, object] = {}
    propagated: list[IRInstruction] = []
    for instruction in instructions:
        opcode = instruction.opcode
        if opcode == "LOAD_NAME":
            name = instruction.operands[0]
            if name in constants:
                propagated.append(IRInstruction("LOAD_CONST", (constants[name],)))
            else:
                propagated.append(instruction)
            continue
        if opcode == "STORE_NAME" and propagated:
            source = propagated[-1]
            destination = instruction.operands[0]
            if source.opcode == "LOAD_CONST":
                constants[destination] = source.operands[0]
            else:
                constants.pop(destination, None)
            propagated.append(instruction)
            continue
        if opcode in {"CALL", "CALL_DYNAMIC", "RETURN", "JUMP", "JUMP_IF_FALSE", "LABEL", "PRINT"}:
            constants.clear()
        propagated.append(instruction)
    return propagated


def constant_folding(instructions: list[IRInstruction]) -> list[IRInstruction]:
    folded: list[IRInstruction] = []
    for instruction in instructions:
        folded.append(instruction)
        changed = True
        while changed:
            changed = False
            if len(folded) >= 3:
                left, right, operator = folded[-3:]
                if left.opcode == right.opcode == "LOAD_CONST" and operator.opcode in PURE_BINARY_OPS:
                    folded[-3:] = [IRInstruction("LOAD_CONST", (evaluate_binary(operator.opcode, left.operands[0], right.operands[0]),))]
                    changed = True
                    continue
            if len(folded) >= 2:
                operand, operator = folded[-2:]
                if operand.opcode == "LOAD_CONST" and operator.opcode in PURE_UNARY_OPS:
                    folded[-2:] = [IRInstruction("LOAD_CONST", (evaluate_unary(operator.opcode, operand.operands[0]),))]
                    changed = True
    return folded


def dead_code_elimination(instructions: list[IRInstruction]) -> list[IRInstruction]:
    cfg = ControlFlowGraph.from_function(type("PseudoFunction", (), {"instructions": instructions})())
    reachable_blocks = cfg.reachable_blocks()
    cleaned: list[IRInstruction] = []
    for block_name, block in cfg.blocks.items():
        if block_name not in reachable_blocks:
            continue
        cleaned.extend(block.instructions)
    if not cleaned:
        return instructions[:1]
    return cleaned


def strength_reduction(instructions: list[IRInstruction]) -> list[IRInstruction]:
    reduced: list[IRInstruction] = []
    index = 0
    while index < len(instructions):
        window = instructions[index:index + 3]
        if len(window) == 3:
            left, right, operator = window
            if operator.opcode == "BINARY_MUL":
                if left.opcode == "LOAD_NAME" and right.opcode == "LOAD_CONST" and right.operands[0] == 2:
                    reduced.extend([left, IRInstruction("LOAD_CONST", (1,)), IRInstruction("BINARY_SHL")])
                    index += 3
                    continue
                if right.opcode == "LOAD_NAME" and left.opcode == "LOAD_CONST" and left.operands[0] == 2:
                    reduced.extend([right, IRInstruction("LOAD_CONST", (1,)), IRInstruction("BINARY_SHL")])
                    index += 3
                    continue
        reduced.append(instructions[index])
        index += 1
    return reduced


def common_subexpression_elimination(instructions: list[IRInstruction]) -> list[IRInstruction]:
    optimized: list[IRInstruction] = []
    cache: dict[tuple, str] = {}
    temp_index = 0
    index = 0
    while index < len(instructions):
        window = instructions[index:index + 3]
        if len(window) == 3 and is_pure_binary_pattern(window):
            signature = pattern_signature(window)
            temp_name = cache.get(signature)
            if temp_name is None:
                temp_name = f"__cse{temp_index}"
                temp_index += 1
                optimized.extend(window)
                optimized.append(IRInstruction("STORE_NAME", (temp_name,)))
                cache[signature] = temp_name
            optimized.append(IRInstruction("LOAD_NAME", (temp_name,)))
            index += 3
            continue
        instruction = instructions[index]
        if instruction.opcode in {"STORE_NAME", "CALL", "CALL_DYNAMIC", "RETURN", "JUMP", "JUMP_IF_FALSE", "LABEL", "PRINT"}:
            cache.clear()
        optimized.append(instruction)
        index += 1
    return optimized


def evaluate_binary(opcode: str, left: object, right: object) -> object:
    if opcode == "BINARY_ADD":
        return left + right
    if opcode == "BINARY_SUB":
        return left - right
    if opcode == "BINARY_MUL":
        return left * right
    if opcode == "BINARY_DIV":
        return left / right
    if opcode == "BINARY_MOD":
        return left % right
    if opcode == "BINARY_SHL":
        return left << right
    if opcode == "BINARY_AND":
        return bool(left) and bool(right)
    if opcode == "BINARY_OR":
        return bool(left) or bool(right)
    if opcode == "COMPARE_EQ":
        return left == right
    if opcode == "COMPARE_NE":
        return left != right
    if opcode == "COMPARE_LT":
        return left < right
    if opcode == "COMPARE_LTE":
        return left <= right
    if opcode == "COMPARE_GT":
        return left > right
    if opcode == "COMPARE_GTE":
        return left >= right
    raise ValueError(f"Unsupported binary opcode {opcode}")


def evaluate_unary(opcode: str, operand: object) -> object:
    if opcode == "UNARY_NEG":
        return -operand
    if opcode == "UNARY_NOT":
        return not bool(operand)
    raise ValueError(f"Unsupported unary opcode {opcode}")


def is_pure_binary_pattern(window: list[IRInstruction]) -> bool:
    left, right, operator = window
    return left.opcode in {"LOAD_CONST", "LOAD_NAME"} and right.opcode in {"LOAD_CONST", "LOAD_NAME"} and operator.opcode in PURE_BINARY_OPS


def pattern_signature(window: list[IRInstruction]) -> tuple:
    left, right, operator = window
    return (
        left.opcode,
        left.operands[0] if left.operands else None,
        right.opcode,
        right.operands[0] if right.operands else None,
        operator.opcode,
    )

