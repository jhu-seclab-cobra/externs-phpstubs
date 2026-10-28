"""Fixed reception counts over the shared C parser and control-flow compiler."""

from collections import deque
from typing import TypeAlias

from handler_index import Compiler
from handler_values import arithmetic
from php_src_c import Program, Source
from php_src_c.definitions import ParseFailure, parse_body
from php_src_c.source import IDENTIFIER

CNode: TypeAlias = tuple['CValue', ...]
CValue: TypeAlias = str | int | None | CNode | list['CValue']
Operation: TypeAlias = tuple[str, list[str]]
CounterState: TypeAlias = tuple[int, frozenset[int]]
MAX_COUNTER_STATES = 10000
PROLOGUE = 'Z_PARAM_PROLOGUE'


def nodes(value: CValue) -> list[CNode]:
    if not isinstance(value, (tuple, list)):
        return []
    own = [value] if isinstance(value, tuple) and value else []
    return own + [node for child in value for node in nodes(child)]


def counter_effect(expression: CValue) -> int | None:
    found = nodes(expression)
    for node in found:
        if node[0] in ('assign', 'post') and ('name', '_i') in nodes(node[2]):
            return None
        if node[0] == 'un' and node[1] == '&' and ('name', '_i') in nodes(node[2]):
            return None
        if node[0] in ('unknown', 'opaque', 'stmtexpr'):
            return None
    prologues = [node for node in found if node[:2] == ('call', ('name', PROLOGUE))]
    if not prologues:
        return 0
    return 1 if expression in prologues and len(prologues) == 1 else None


def constant(node: CNode) -> int | None:
    match node:
        case ('num', value) if isinstance(value, int):
            return value
        case ('cast', _, value):
            return constant(value)
        case ('un', '!', value):
            result = constant(value)
            return None if result is None else int(not result)
        case ('bin', operator, left, right):
            first, second = constant(left), constant(right)
            return None if first is None or second is None else arithmetic(operator, first, second)
    return None


def successors(instruction: CNode, pc: int) -> list[int] | None:
    match instruction:
        case ('j', target):
            return [target]
        case ('b', condition, then, otherwise):
            value = constant(condition)
            return [then, otherwise] if value is None else [then if value else otherwise]
        case ('n',) | ('x', _) | ('d', _, _, _, _, _):
            return [pc + 1]
        case ('r', _):
            return []
    return None


def instruction_effect(instruction: CNode) -> int | None:
    match instruction:
        case ('d', '_i', _, _, _, _):
            return None
        case ('d', _, _, _, initial, _):
            return counter_effect(initial)
        case ('x', expression) | ('r', expression) | ('b', expression, _, _):
            return counter_effect(expression)
        case ('n',) | ('j', _):
            return 0
    return None


def count_paths(instructions: list[CNode]) -> int | None:
    pending: deque[CounterState] = deque([(0, frozenset())])
    prologues = frozenset(pc for pc, instruction in enumerate(instructions) if instruction_effect(instruction) == 1)
    exits: set[frozenset[int]] = set()
    visited = 0
    while pending:
        pc, trail = pending.popleft()
        visited += 1
        if pc in trail or visited > MAX_COUNTER_STATES:
            return None
        step, targets = instruction_effect(instructions[pc]), successors(instructions[pc], pc)
        if step is None or targets is None:
            return None
        if not targets:
            exits.add((trail | {pc}) & prologues)
        pending.extend((target, trail | {pc}) for target in targets)
    return len(next(iter(exits))) if len(exits) == 1 else None


def reception_count(program: Program, source: Source, operation: Operation) -> int | None:
    name, arguments = operation
    macro = program.preprocessor.lookup(source, name)
    if macro is None:
        return None
    admitted = frozenset({PROLOGUE, 'EXPECTED', 'UNEXPECTED'})
    text = program.preprocessor.expand(f'{name}({", ".join(arguments)})', source, admitted)
    if any(word not in admitted and program.preprocessor.lookup(source, word) is not None
           for word in IDENTIFIER.findall(text)):
        return None
    try:
        block = parse_body('{ do {' + text + '} while (0); }')
    except ParseFailure:
        return None
    if block.opaque:
        return None
    code = Compiler().compile(block)
    return None if code.failure else count_paths(code.instrs)
