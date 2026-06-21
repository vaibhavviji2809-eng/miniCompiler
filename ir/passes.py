from __future__ import annotations

from collections import defaultdict

from .ir_instruction import IRInstruction


def constant_propagation(instructions: list[IRInstruction]) -> list[IRInstruction]:
    propagated: list[IRInstruction] = []
    constants: dict[str, object] = {}
    for instruction in instructions:
        opcode = instruction.opcode
        if opcode == "LOAD_NAME" and instruction.operands[0] in constants:
            propagated.append(IRInstruction("LOAD_CONST", (constants[instruction.operands[0]],)))
            continue
        if opcode == "STORE_NAME":
            if propagated and propagated[-1].opcode == "LOAD_CONST":
                constants[instruction.operands[0]] = propagated[-1].operands[0]
            else:
                constants.pop(instruction.operands[0], None)
            propagated.append(instruction)
            continue
        if opcode in {"CALL", "CALL_DYNAMIC", "RETURN", "JUMP", "JUMP_IF_FALSE", "LABEL"}:
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
                if left.opcode == right.opcode == "LOAD_CONST" and operator.opcode in BINARY_OPERATIONS:
                    result = evaluate_binary(operator.opcode, left.operands[0], right.operands[0])
                    folded[-3:] = [IRInstruction("LOAD_CONST", (result,))]
                    changed = True
                    continue
            if len(folded) >= 2:
                operand, operator = folded[-2:]
                if operand.opcode == "LOAD_CONST" and operator.opcode in UNARY_OPERATIONS:
                    result = evaluate_unary(operator.opcode, operand.operands[0])
                    folded[-2:] = [IRInstruction("LOAD_CONST", (result,))]
                    changed = True
    return folded


def dead_code_elimination(instructions: list[IRInstruction]) -> list[IRInstruction]:
    cleaned: list[IRInstruction] = []
    skipping = False
    for instruction in instructions:
        if skipping:
            if instruction.opcode == "LABEL":
                skipping = False
                cleaned.append(instruction)
            continue
        cleaned.append(instruction)
        if instruction.opcode in {"RETURN", "JUMP"}:
            skipping = True
    return cleaned


def strength_reduction(instructions: list[IRInstruction]) -> list[IRInstruction]:
    reduced: list[IRInstruction] = []
    for instruction in instructions:
        if instruction.opcode == "BINARY_MUL" and len(reduced) >= 1:
            previous = reduced[-1]
            if previous.opcode == "LOAD_CONST" and previous.operands[0] == 2:
                reduced[-1] = IRInstruction("LOAD_CONST", (1,))
                reduced.append(IRInstruction("BINARY_SHL"))
                continue
        reduced.append(instruction)
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
                optimized.append(IRInstruction("LOAD_NAME", (temp_name,)))
                cache[signature] = temp_name
            else:
                optimized.append(IRInstruction("LOAD_NAME", (temp_name,)))
            index += 3
            continue
        instruction = instructions[index]
        if instruction.opcode in {"STORE_NAME", "CALL", "CALL_DYNAMIC", "JUMP", "JUMP_IF_FALSE", "RETURN", "LABEL"}:
            cache.clear()
        optimized.append(instruction)
        index += 1
    return optimized


BINARY_OPERATIONS = {
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

UNARY_OPERATIONS = {"UNARY_NEG", "UNARY_NOT"}


def is_pure_binary_pattern(window: list[IRInstruction]) -> bool:
    left, right, operator = window
    return left.opcode in {"LOAD_CONST", "LOAD_NAME"} and right.opcode in {"LOAD_CONST", "LOAD_NAME"} and operator.opcode in {
        "BINARY_ADD",
        "BINARY_SUB",
        "BINARY_MUL",
        "BINARY_DIV",
        "BINARY_MOD",
        "COMPARE_EQ",
        "COMPARE_NE",
        "COMPARE_LT",
        "COMPARE_LTE",
        "COMPARE_GT",
        "COMPARE_GTE",
    }


def pattern_signature(window: list[IRInstruction]) -> tuple:
    left, right, operator = window
    return (
        left.opcode,
        left.operands[0] if left.operands else None,
        right.opcode,
        right.operands[0] if right.operands else None,
        operator.opcode,
    )


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

