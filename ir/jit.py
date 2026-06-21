from __future__ import annotations

from dataclasses import dataclass, field

from .ir_instruction import IRFunction, IRInstruction, IRProgram


@dataclass(slots=True)
class MachineInstruction:
    opcode: str
    operands: tuple[object, ...] = ()


@dataclass(slots=True)
class MachineFunction:
    name: str
    params: list[str] = field(default_factory=list)
    instructions: list[MachineInstruction] = field(default_factory=list)


@dataclass(slots=True)
class MachineProgram:
    main: MachineFunction
    functions: dict[str, MachineFunction] = field(default_factory=dict)


class JITCompiler:
    def compile_program(self, program: IRProgram) -> MachineProgram:
        main = self.compile_function(program.main)
        functions = {name: self.compile_function(function) for name, function in program.functions.items()}
        return MachineProgram(main=main, functions=functions)

    def compile_function(self, function: IRFunction) -> MachineFunction:
        label_map = self.build_label_map(function.instructions)
        machine = MachineFunction(name=function.name, params=function.params.copy())
        stack: list[str] = []
        register_index = 0

        def new_register() -> str:
            nonlocal register_index
            register = f"r{register_index}"
            register_index += 1
            return register

        for instruction in function.instructions:
            opcode = instruction.opcode
            if opcode == "LABEL":
                continue
            if opcode == "LOAD_CONST":
                register = new_register()
                machine.instructions.append(MachineInstruction("MOV_CONST", (register, instruction.operands[0])))
                stack.append(register)
                continue
            if opcode == "LOAD_NAME":
                register = new_register()
                machine.instructions.append(MachineInstruction("LOAD_LOCAL", (register, instruction.operands[0])))
                stack.append(register)
                continue
            if opcode == "STORE_NAME":
                register = stack.pop()
                machine.instructions.append(MachineInstruction("STORE_LOCAL", (instruction.operands[0], register)))
                continue
            if opcode == "BUILD_ARRAY":
                count = instruction.operands[0]
                values = [stack.pop() for _ in range(count)][::-1]
                destination = new_register()
                machine.instructions.append(MachineInstruction("BUILD_ARRAY", (destination, tuple(values))))
                stack.append(destination)
                continue
            if opcode == "BUILD_STRUCT":
                struct_name, field_names, count = instruction.operands
                values = [stack.pop() for _ in range(count)][::-1]
                destination = new_register()
                machine.instructions.append(MachineInstruction("BUILD_STRUCT", (destination, struct_name, field_names, tuple(values))))
                stack.append(destination)
                continue
            if opcode == "LOAD_INDEX":
                index = stack.pop()
                target = stack.pop()
                destination = new_register()
                machine.instructions.append(MachineInstruction("LOAD_INDEX", (destination, target, index)))
                stack.append(destination)
                continue
            if opcode == "LOAD_MEMBER":
                target = stack.pop()
                destination = new_register()
                machine.instructions.append(MachineInstruction("LOAD_MEMBER", (destination, target, instruction.operands[0])))
                stack.append(destination)
                continue
            if opcode == "POP":
                if stack:
                    stack.pop()
                continue
            if opcode in {"UNARY_NEG", "UNARY_NOT"}:
                operand = stack.pop()
                destination = new_register()
                machine.instructions.append(MachineInstruction(opcode, (destination, operand)))
                stack.append(destination)
                continue
            if opcode in {
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
            }:
                right = stack.pop()
                left = stack.pop()
                destination = new_register()
                machine.instructions.append(MachineInstruction(opcode, (destination, left, right)))
                stack.append(destination)
                continue
            if opcode == "JUMP":
                machine.instructions.append(MachineInstruction("JUMP", (label_map[instruction.operands[0]],)))
                continue
            if opcode == "JUMP_IF_FALSE":
                condition = stack.pop()
                machine.instructions.append(MachineInstruction("JUMP_IF_FALSE", (condition, label_map[instruction.operands[0]])))
                continue
            if opcode == "PRINT":
                value = stack.pop()
                machine.instructions.append(MachineInstruction("PRINT", (value,)))
                continue
            if opcode == "CALL":
                function_name, argument_count = instruction.operands
                arguments = [stack.pop() for _ in range(argument_count)][::-1]
                destination = new_register()
                machine.instructions.append(MachineInstruction("CALL", (destination, function_name, tuple(arguments))))
                stack.append(destination)
                continue
            if opcode == "CALL_DYNAMIC":
                argument_count = instruction.operands[0]
                arguments = [stack.pop() for _ in range(argument_count)][::-1]
                callee = stack.pop()
                destination = new_register()
                machine.instructions.append(MachineInstruction("CALL_DYNAMIC", (destination, callee, tuple(arguments))))
                stack.append(destination)
                continue
            if opcode == "RETURN":
                result = stack.pop() if stack else None
                machine.instructions.append(MachineInstruction("RETURN", (result,)))
                continue
            raise ValueError(f"Unsupported IR opcode {opcode}")
        return machine

    def build_label_map(self, instructions: list[IRInstruction]) -> dict[str, int]:
        label_map: dict[str, int] = {}
        address = 0
        for instruction in instructions:
            if instruction.opcode == "LABEL":
                label_map[instruction.operands[0]] = address
            else:
                address += 1
        return label_map


class MachineRuntime:
    def __init__(self, program: MachineProgram) -> None:
        self.program = program
        self.outputs: list[object] = []
        self.globals: dict[str, object] = {}

    def run(self) -> object | None:
        return self.execute_function("main", [], is_main=True)

    def execute_function(self, name: str, arguments: list[object], is_main: bool = False) -> object | None:
        function = self.program.main if is_main else self.program.functions[name]
        registers: dict[str, object] = {}
        locals_: dict[str, object] = {}
        for parameter, argument in zip(function.params, arguments):
            locals_[parameter] = argument
        ip = 0
        while ip < len(function.instructions):
            instruction = function.instructions[ip]
            ip += 1
            opcode = instruction.opcode
            if opcode == "MOV_CONST":
                destination, value = instruction.operands
                registers[destination] = value
            elif opcode == "LOAD_LOCAL":
                destination, name = instruction.operands
                registers[destination] = locals_.get(name, self.globals.get(name))
            elif opcode == "STORE_LOCAL":
                name, source = instruction.operands
                locals_[name] = registers[source]
                if is_main:
                    self.globals[name] = registers[source]
            elif opcode == "BUILD_ARRAY":
                destination, values = instruction.operands
                registers[destination] = [registers[value] for value in values]
            elif opcode == "BUILD_STRUCT":
                destination, struct_name, field_names, values = instruction.operands
                registers[destination] = {"__struct__": struct_name, **{field_name: registers[value] for field_name, value in zip(field_names, values)}}
            elif opcode == "LOAD_INDEX":
                destination, target, index = instruction.operands
                registers[destination] = registers[target][registers[index]]
            elif opcode == "LOAD_MEMBER":
                destination, target, member = instruction.operands
                target_value = registers[target]
                if isinstance(target_value, dict):
                    registers[destination] = target_value[member]
                else:
                    registers[destination] = getattr(target_value, member)
            elif opcode == "UNARY_NEG":
                destination, source = instruction.operands
                registers[destination] = -registers[source]
            elif opcode == "UNARY_NOT":
                destination, source = instruction.operands
                registers[destination] = not bool(registers[source])
            elif opcode in {
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
            }:
                destination, left, right = instruction.operands
                registers[destination] = self.execute_binary(opcode, registers[left], registers[right])
            elif opcode == "JUMP":
                ip = instruction.operands[0]
            elif opcode == "JUMP_IF_FALSE":
                condition, target = instruction.operands
                if not self.is_truthy(registers[condition]):
                    ip = target
            elif opcode == "PRINT":
                self.outputs.append(registers[instruction.operands[0]])
            elif opcode == "CALL":
                destination, function_name, argument_registers = instruction.operands
                arguments = [registers[register] for register in argument_registers]
                registers[destination] = self.execute_function(function_name, arguments)
            elif opcode == "CALL_DYNAMIC":
                destination, callee_register, argument_registers = instruction.operands
                callee = registers[callee_register]
                arguments = [registers[register] for register in argument_registers]
                if isinstance(callee, str) and callee in self.program.functions:
                    registers[destination] = self.execute_function(callee, arguments)
                elif callable(callee):
                    registers[destination] = callee(*arguments)
                else:
                    raise RuntimeError("Unsupported dynamic call target")
            elif opcode == "RETURN":
                result = instruction.operands[0]
                if isinstance(result, str):
                    resolved = registers[result]
                    if resolved is not None:
                        return resolved
                    if self.outputs:
                        return self.outputs[-1]
                    return None
                if result is not None:
                    return result
                if self.outputs:
                    return self.outputs[-1]
                return None
            else:
                raise RuntimeError(f"Unsupported machine opcode {opcode}")
        return None

    def execute_binary(self, opcode: str, left: object, right: object) -> object:
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
        raise RuntimeError(f"Unsupported machine opcode {opcode}")

    def is_truthy(self, value: object) -> bool:
        return bool(value)
