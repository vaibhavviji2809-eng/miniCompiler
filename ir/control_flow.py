from __future__ import annotations

from dataclasses import dataclass, field

from .ir_instruction import IRFunction, IRInstruction


@dataclass(slots=True)
class BasicBlock:
    name: str
    instructions: list[IRInstruction] = field(default_factory=list)
    predecessors: set[str] = field(default_factory=set)
    successors: set[str] = field(default_factory=set)

    def terminator(self) -> IRInstruction | None:
        return self.instructions[-1] if self.instructions else None


@dataclass(slots=True)
class ControlFlowGraph:
    entry: str
    blocks: dict[str, BasicBlock]

    @classmethod
    def from_function(cls, function: IRFunction) -> ControlFlowGraph:
        blocks = build_basic_blocks(function.instructions)
        link_blocks(blocks)
        entry = next(iter(blocks)) if blocks else "entry"
        return cls(entry=entry, blocks=blocks)

    def reachable_blocks(self) -> set[str]:
        seen: set[str] = set()
        stack = [self.entry]
        while stack:
            name = stack.pop()
            if name in seen or name not in self.blocks:
                continue
            seen.add(name)
            stack.extend(self.blocks[name].successors)
        return seen

    def to_instruction_list(self) -> list[IRInstruction]:
        instructions: list[IRInstruction] = []
        for block in self.blocks.values():
            instructions.extend(block.instructions)
        return instructions


def build_basic_blocks(instructions: list[IRInstruction]) -> dict[str, BasicBlock]:
    leaders = {0}
    label_to_index: dict[str, int] = {}
    for index, instruction in enumerate(instructions):
        if instruction.opcode == "LABEL":
            label_to_index[instruction.operands[0]] = index
            leaders.add(index)
        if instruction.opcode in {"JUMP", "JUMP_IF_FALSE", "RETURN"} and index + 1 < len(instructions):
            leaders.add(index + 1)
            if instruction.operands and isinstance(instruction.operands[0], str):
                leaders.add(label_to_index.get(instruction.operands[0], index))
    sorted_leaders = sorted(leader for leader in leaders if leader < len(instructions))
    if not sorted_leaders:
        return {}
    blocks: dict[str, BasicBlock] = {}
    block_names: list[str] = []
    for block_index, start in enumerate(sorted_leaders):
        end = sorted_leaders[block_index + 1] if block_index + 1 < len(sorted_leaders) else len(instructions)
        block_name = f"B{block_index}"
        block_names.append(block_name)
        blocks[block_name] = BasicBlock(name=block_name, instructions=instructions[start:end])
    # Merge leading labels into the current block name map.
    remapped: dict[str, BasicBlock] = {}
    current_name = None
    for block_name in block_names:
        block = blocks[block_name]
        if current_name is None:
            current_name = block_name
        remapped[block_name] = block
    return remapped


def link_blocks(blocks: dict[str, BasicBlock]) -> None:
    block_names = list(blocks)
    label_to_block: dict[str, str] = {}
    for block_name, block in blocks.items():
        for instruction in block.instructions:
            if instruction.opcode == "LABEL":
                label_to_block[instruction.operands[0]] = block_name
                break
    for index, block_name in enumerate(block_names):
        block = blocks[block_name]
        terminator = block.terminator()
        if terminator is None:
            if index + 1 < len(block_names):
                successor = block_names[index + 1]
                block.successors.add(successor)
                blocks[successor].predecessors.add(block_name)
            continue
        if terminator.opcode == "JUMP":
            target = label_to_block.get(terminator.operands[0])
            if target is not None:
                block.successors.add(target)
                blocks[target].predecessors.add(block_name)
        elif terminator.opcode == "JUMP_IF_FALSE":
            target = label_to_block.get(terminator.operands[0])
            if target is not None:
                block.successors.add(target)
                blocks[target].predecessors.add(block_name)
            if index + 1 < len(block_names):
                fallthrough = block_names[index + 1]
                block.successors.add(fallthrough)
                blocks[fallthrough].predecessors.add(block_name)
        elif terminator.opcode != "RETURN" and index + 1 < len(block_names):
            successor = block_names[index + 1]
            block.successors.add(successor)
            blocks[successor].predecessors.add(block_name)


def compute_dominators(cfg: ControlFlowGraph) -> dict[str, set[str]]:
    blocks = set(cfg.blocks)
    dominators = {name: set(blocks) for name in blocks}
    if cfg.entry in dominators:
        dominators[cfg.entry] = {cfg.entry}
    changed = True
    while changed:
        changed = False
        for name, block in cfg.blocks.items():
            if name == cfg.entry:
                continue
            predecessors = block.predecessors
            if not predecessors:
                continue
            candidate = {name}.union(*(dominators[pred] for pred in predecessors if pred in dominators))
            intersection = set(blocks)
            for predecessor in predecessors:
                intersection &= dominators.get(predecessor, set())
            new_dominators = intersection | {name}
            if new_dominators != dominators[name]:
                dominators[name] = new_dominators
                changed = True
    return dominators


def detect_loops(cfg: ControlFlowGraph) -> list[tuple[str, str]]:
    dominators = compute_dominators(cfg)
    loops: list[tuple[str, str]] = []
    for source, block in cfg.blocks.items():
        for target in block.successors:
            if target in dominators.get(source, set()):
                loops.append((source, target))
    return loops

