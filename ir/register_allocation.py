from __future__ import annotations

from dataclasses import dataclass, field

from .control_flow import ControlFlowGraph, compute_dominators
from .ir_instruction import IRFunction, IRInstruction


@dataclass(slots=True)
class LivenessResult:
    live_in: dict[str, set[str]] = field(default_factory=dict)
    live_out: dict[str, set[str]] = field(default_factory=dict)
    instruction_live_out: list[set[str]] = field(default_factory=list)


@dataclass(slots=True)
class RegisterAllocationResult:
    register_map: dict[str, int] = field(default_factory=dict)
    spill_slots: dict[str, int] = field(default_factory=dict)
    interference_graph: dict[str, set[str]] = field(default_factory=dict)
    liveness: LivenessResult = field(default_factory=LivenessResult)


def live_variable_analysis(function: IRFunction) -> LivenessResult:
    cfg = ControlFlowGraph.from_function(function)
    block_use: dict[str, set[str]] = {}
    block_def: dict[str, set[str]] = {}
    block_live_in: dict[str, set[str]] = {name: set() for name in cfg.blocks}
    block_live_out: dict[str, set[str]] = {name: set() for name in cfg.blocks}
    instruction_live_out: list[set[str]] = [set() for _ in function.instructions]

    block_ranges = block_instruction_ranges(cfg, function.instructions)
    for block_name, block in cfg.blocks.items():
        use, defined = compute_use_def(block.instructions)
        block_use[block_name] = use
        block_def[block_name] = defined

    changed = True
    while changed:
        changed = False
        for block_name in reversed(list(cfg.blocks)):
            successors = cfg.blocks[block_name].successors
            out_set = set().union(*(block_live_in[successor] for successor in successors if successor in block_live_in))
            in_set = block_use[block_name] | (out_set - block_def[block_name])
            if out_set != block_live_out[block_name] or in_set != block_live_in[block_name]:
                block_live_out[block_name] = out_set
                block_live_in[block_name] = in_set
                changed = True

    for block_name, block in cfg.blocks.items():
        live = set(block_live_out[block_name])
        start, end = block_ranges[block_name]
        for index in range(end - 1, start - 1, -1):
            instruction = function.instructions[index]
            instruction_live_out[index] = live.copy()
            uses, defines = instruction_use_def(instruction)
            live -= defines
            live |= uses

    return LivenessResult(live_in=block_live_in, live_out=block_live_out, instruction_live_out=instruction_live_out)


def allocate_registers(function: IRFunction, register_count: int = 8) -> RegisterAllocationResult:
    liveness = live_variable_analysis(function)
    graph = build_interference_graph(function, liveness)
    register_map, spill_slots = color_interference_graph(graph, register_count)
    return RegisterAllocationResult(
        register_map=register_map,
        spill_slots=spill_slots,
        interference_graph=graph,
        liveness=liveness,
    )


def build_interference_graph(function: IRFunction, liveness: LivenessResult) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    live_after = liveness.instruction_live_out
    for index, instruction in enumerate(function.instructions):
        uses, defines = instruction_use_def(instruction)
        for defined in defines:
            graph.setdefault(defined, set())
            for live_name in live_after[index]:
                if live_name == defined:
                    continue
                graph.setdefault(live_name, set()).add(defined)
                graph[defined].add(live_name)
        for used in uses:
            graph.setdefault(used, set())
    return graph


def color_interference_graph(graph: dict[str, set[str]], register_count: int) -> tuple[dict[str, int], dict[str, int]]:
    ordering = sorted(graph, key=lambda name: len(graph[name]), reverse=True)
    register_map: dict[str, int] = {}
    spill_slots: dict[str, int] = {}
    next_spill = 0
    for name in ordering:
        used_registers = {register_map[neighbor] for neighbor in graph[name] if neighbor in register_map}
        for register in range(register_count):
            if register not in used_registers:
                register_map[name] = register
                break
        else:
            spill_slots[name] = next_spill
            next_spill += 1
    return register_map, spill_slots


def compute_use_def(instructions: list[IRInstruction]) -> tuple[set[str], set[str]]:
    live_use: set[str] = set()
    live_def: set[str] = set()
    for instruction in instructions:
        uses, defines = instruction_use_def(instruction)
        live_use |= uses - live_def
        live_def |= defines
    return live_use, live_def


def instruction_use_def(instruction: IRInstruction) -> tuple[set[str], set[str]]:
    opcode = instruction.opcode
    operands = instruction.operands
    if opcode == "LOAD_NAME":
        return {operands[0]}, set()
    if opcode == "STORE_NAME":
        return set(), {operands[0]}
    if opcode == "CALL":
        return set(), set()
    if opcode == "CALL_DYNAMIC":
        return set(), set()
    if opcode == "JUMP" or opcode == "JUMP_IF_FALSE" or opcode == "LABEL" or opcode == "RETURN" or opcode == "PRINT":
        return set(), set()
    return set(), set()


def block_instruction_ranges(cfg: ControlFlowGraph, instructions: list[IRInstruction]) -> dict[str, tuple[int, int]]:
    ranges: dict[str, tuple[int, int]] = {}
    cursor = 0
    for name, block in cfg.blocks.items():
        size = len(block.instructions)
        ranges[name] = (cursor, cursor + size)
        cursor += size
    return ranges

