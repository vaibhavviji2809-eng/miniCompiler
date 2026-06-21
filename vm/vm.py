from __future__ import annotations

from .runtime import Frame, Runtime
from ..bytecode.bytecode import BytecodeProgram, Instruction
from ..bytecode.opcode import Opcode


class VirtualMachine:
    def __init__(self, program: BytecodeProgram) -> None:
        self.runtime = Runtime(program)
        self.outputs: list[object] = []

    def run(self) -> object | None:
        current = self.runtime.create_frame("main", is_main=True)
        call_stack: list[Frame] = []
        last_value: object | None = None

        while True:
            if current.ip >= len(current.function.instructions):
                if call_stack:
                    current = call_stack.pop()
                    continue
                break

            instruction = current.function.instructions[current.ip]
            current.ip += 1
            opcode = instruction.opcode

            if opcode == Opcode.LOAD_CONST:
                current.stack.push(instruction.operands[0])
                continue
            if opcode == Opcode.LOAD_NAME:
                current.stack.push(self.runtime.load_name(current, instruction.operands[0]))
                continue
            if opcode == Opcode.STORE_NAME:
                value = current.stack.pop()
                self.runtime.store_name(current, instruction.operands[0], value)
                last_value = value
                continue
            if opcode == Opcode.POP:
                if len(current.stack) > 0:
                    last_value = current.stack.pop()
                continue
            if opcode == Opcode.UNARY_NEG:
                current.stack.push(-current.stack.pop())
                continue
            if opcode == Opcode.UNARY_NOT:
                current.stack.push(not bool(current.stack.pop()))
                continue
            if opcode in {
                Opcode.BINARY_ADD,
                Opcode.BINARY_SUB,
                Opcode.BINARY_MUL,
                Opcode.BINARY_DIV,
                Opcode.BINARY_MOD,
                Opcode.BINARY_SHL,
                Opcode.BINARY_AND,
                Opcode.BINARY_OR,
                Opcode.COMPARE_EQ,
                Opcode.COMPARE_NE,
                Opcode.COMPARE_LT,
                Opcode.COMPARE_LTE,
                Opcode.COMPARE_GT,
                Opcode.COMPARE_GTE,
            }:
                right = current.stack.pop()
                left = current.stack.pop()
                current.stack.push(self.execute_binary(opcode, left, right))
                continue
            if opcode == Opcode.JUMP:
                current.ip = instruction.operands[0]
                continue
            if opcode == Opcode.JUMP_IF_FALSE:
                condition = current.stack.pop()
                if not self.is_truthy(condition):
                    current.ip = instruction.operands[0]
                continue
            if opcode == Opcode.PRINT:
                value = current.stack.pop()
                self.outputs.append(value)
                last_value = value
                continue
            if opcode == Opcode.CALL:
                function_name, argument_count = instruction.operands
                arguments = [current.stack.pop() for _ in range(argument_count)][::-1]
                call_stack.append(current)
                current = self.runtime.create_frame(function_name, arguments)
                continue
            if opcode == Opcode.CALL_DYNAMIC:
                argument_count = instruction.operands[0]
                arguments = [current.stack.pop() for _ in range(argument_count)][::-1]
                callee = current.stack.pop()
                if isinstance(callee, str) and callee in self.runtime.program.functions:
                    call_stack.append(current)
                    current = self.runtime.create_frame(callee, arguments)
                    continue
                if callable(callee):
                    current.stack.push(callee(*arguments))
                    continue
                raise RuntimeError("Unsupported dynamic call target")
            if opcode == Opcode.RETURN:
                result = current.stack.pop() if len(current.stack) > 0 else None
                last_value = result
                if call_stack:
                    current = call_stack.pop()
                    current.stack.push(result)
                    continue
                if result is not None:
                    return result
                if self.outputs:
                    return self.outputs[-1]
                return None
            raise RuntimeError(f"Unsupported opcode {opcode}")

        if self.outputs:
            return self.outputs[-1]
        if last_value is not None:
            return last_value
        return None

    def execute_binary(self, opcode: Opcode, left: object, right: object) -> object:
        if opcode == Opcode.BINARY_ADD:
            return left + right
        if opcode == Opcode.BINARY_SUB:
            return left - right
        if opcode == Opcode.BINARY_MUL:
            return left * right
        if opcode == Opcode.BINARY_DIV:
            return left / right
        if opcode == Opcode.BINARY_MOD:
            return left % right
        if opcode == Opcode.BINARY_SHL:
            return left << right
        if opcode == Opcode.BINARY_AND:
            return bool(left) and bool(right)
        if opcode == Opcode.BINARY_OR:
            return bool(left) or bool(right)
        if opcode == Opcode.COMPARE_EQ:
            return left == right
        if opcode == Opcode.COMPARE_NE:
            return left != right
        if opcode == Opcode.COMPARE_LT:
            return left < right
        if opcode == Opcode.COMPARE_LTE:
            return left <= right
        if opcode == Opcode.COMPARE_GT:
            return left > right
        if opcode == Opcode.COMPARE_GTE:
            return left >= right
        raise RuntimeError(f"Unsupported binary opcode {opcode}")

    def is_truthy(self, value: object) -> bool:
        return bool(value)
