"""Named-collection transport using the existing C control-flow and memory machine."""

from copy import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from handler_index import STRUCT_BODY, Compiled, Compiler, Index
from handler_machine import Frame, Machine
from handler_memory import ANYV, SYMBOLIC, Agg, Alt, Fill, Fn, Masked, Ptr, Region, Size, Str, Sym, Test, Unknown, State
from handler_summary import SummaryPolicy
from handler_world import World
from named_extras_bindings import shadowed_bindings
from named_extras_context import CONTEXT_SOURCE, INI_SOURCE, OBJECT_SOURCE, read_protocols, source_api, strlen_api, target_api
from named_extras_reception import CNode
from php_src_c import Program, Source
from php_src_c.definitions import Definition, ParseFailure, ParsedBlock, parse_body
from php_src_c.source import STRING_PLACEHOLDER

Value: TypeAlias = int | Ptr | Fn | Str | Sym | Unknown | Alt | Agg | Size | Masked | Test | Fill
Outcome: TypeAlias = tuple[Value, State]
PARSED = Sym('named-extras:parsed')
PARSE = '__named_extras_parse'
TARGETS = frozenset({'zend_call_function', 'zend_call_known_function', 'zend_call_known_fcc'})
CONTEXT_APIS = frozenset({'zend_fiber_init_context', 'zend_fiber_resume_internal'})
SAVE_CONTEXT = frozenset({'setjmp', '_setjmp', 'sigsetjmp'})
RESTORE_CONTEXT = frozenset({'longjmp', '_longjmp', 'siglongjmp'})
FLOW_BUDGET = 150000
UNREAD_CONTROL = 'named-extras:unread-control'
UNREAD_VALUE = 'named-extras:unread-value'


@dataclass(frozen=True)
class ParsedCollection:
    start: int
    end: int
    destination: str
    inputs: tuple[str, ...]
    parameters: tuple[int, ...] = ()


def control_flow(code: Compiled) -> Compiled:
    instructions = [('o', str(instruction[1])) if instruction[0] == 'x' and instruction[1][0] == 'name'
                    else instruction for instruction in code.instrs]
    return Compiled(instructions, code.labels, code.heads, code.failure, code.opaque)


class FlowIndex(Index):
    def layout(self) -> list[str]:
        # Small parsing fixtures have no object handlers; real object dispatch uses the existing layout reader.
        return super().layout() if any(STRUCT_BODY.search(s.text) for s in self.program.sources) else []

    def compile(self, definition: Definition) -> Compiled:
        disabled = self.disabled | TARGETS | CONTEXT_APIS | {PARSE}
        if strlen_api(self, definition.source):
            disabled = disabled | {'strlen'}
        text = self.pre.expand(definition.body, definition.source, disabled)
        try:
            block = parse_body(text, definition.params)
            shadowed = shadowed_bindings(block, frozenset(definition.params))
            if shadowed:
                return Compiled([], {}, set(), f'unestablished lexical bindings: {", ".join(sorted(shadowed))}')
            return control_flow(Compiler(definition.source.otherwise).compile(block))
        except ParseFailure as failure:
            return Compiled([], {}, set(), str(failure))

    def inline(self, block: ParsedBlock, source: Source) -> Compiled:
        return control_flow(super().inline(block, source))


def pointer(value: Value) -> Ptr | None:
    if isinstance(value, Sym):
        return value.pointer()
    return value if isinstance(value, Ptr) else None


def unread(value: Value) -> bool:
    if isinstance(value, (Masked, Test)):
        value = value.sym
    return isinstance(value, Sym) and UNREAD_VALUE in value.sid


def object_label(value: Value) -> str:
    return f'named-extras:object:{pointer(value)!r}'


def literal_length(program: Program, value: Value) -> int | None:
    match = STRING_PLACEHOLDER.fullmatch(value) if isinstance(value, Str) else None
    text = program.strings[int(match[1])] if match else None
    return len(text) if text is not None and '\\' not in text and text.isascii() else None


def call_state(world: World) -> State:
    state = State(world)
    state.put('g:execute_data', Region(SYMBOLIC, {(): Ptr('o:call-frame', ())}))
    state.put('g:return_value', Region(SYMBOLIC, {(): Ptr('o:call-result', ())}))
    state.put('o:call-frame', Region(SYMBOLIC, {('This', 'value'): Ptr('o:receiver', ('std',))}))
    state.put('o:receiver', Region(SYMBOLIC))
    state.put('o:call-result', Region(SYMBOLIC))
    state.write('o:call-frame', ('extra_named_params',), PARSED)
    state.put(PARSED.pointer().rid, Region(SYMBOLIC))
    state.watch = frozenset({PARSED.pointer().rid})
    return state


class FlowMachine(Machine):
    index: FlowIndex

    def __init__(self, index: FlowIndex) -> None:
        super().__init__(index, SummaryPolicy())
        self.forwarded = False
        self.protocols = read_protocols(index)

    @staticmethod
    def fork_on(value: Value, state: State) -> list[tuple[bool, State]]:
        if unread(value):
            state.flags = state.flags | {UNREAD_CONTROL}
        return Machine.fork_on(value, state)

    def _unread_memory(self, args: list[Value], state: State) -> None:
        for argument in args:
            target = pointer(argument)
            if target is not None:
                state.havoc(target.rid, target.path)

    def unknown_call(self, args: list[Value], state: State) -> list[Outcome]:
        self._unread_memory(args, state)
        state.flags = state.flags | {UNREAD_CONTROL}
        state.serial += 1
        return [(Sym(f'{UNREAD_VALUE}:{state.serial}'), state)]

    def i_o(self, instruction: CNode, pc: int, state: State, frame: Frame,
            push: Callable[[int, State], None], exits: list[Outcome]) -> None:
        state.flags = state.flags | {UNREAD_CONTROL}
        super().i_o(instruction, pc, state, frame, push, exits)

    def apply_binary(self, operator: str, left: Value, right: Value, state: State) -> list[Outcome]:
        if unread(left) or unread(right):
            return [(Sym(UNREAD_VALUE), state)]
        return super().apply_binary(operator, left, right, state)

    @staticmethod
    def unary(operator: str, value: Value) -> Value:
        return value if unread(value) else Machine.unary(operator, value)

    def invoke(self, callee: CNode, args: list[Value], state: State, frame: Frame) -> list[Outcome]:
        if not (self.protocols.constructors and callee[0] == 'member' and callee[2] == 'get_constructor'
                and callee[1][0] == 'member' and callee[1][2] == 'handlers'):
            return super().invoke(callee, args, state, frame)
        objects = self.ev(callee[1][1], state, frame)
        if not objects or any(object_label(value) not in member.flags for value, member in objects):
            return super().invoke(callee, args, state, frame)
        outcomes: list[Outcome] = []
        for target, member in self.ev(callee, state, frame):
            if isinstance(target, (Fn, int)):
                outcomes.extend(self.call_value(target, args, member, frame))
            else:
                self._unread_memory(args, member)
                outcomes.append((Sym('named-extras:constructor'), member))
        return outcomes

    def _parse_collection(self, args: list[Value], state: State) -> list[Outcome]:
        for argument in args[:-1]:
            target = pointer(argument)
            if target is not None:
                state.write(target.rid, target.path, Fill(SYMBOLIC))
        target = pointer(args[-1])
        if target is not None:
            state.write(target.rid, target.path, state.read('o:call-frame', ('extra_named_params',)))
        return [(ANYV, state)]

    def _target_call(self, name: str, args: list[Value], execution: tuple[State, Frame]) -> list[Outcome]:
        state, frame = execution
        info = pointer(args[0]) if args else None
        named = self.load(Ptr(info.rid, info.path + ('named_params',)), state) if info else ANYV
        collection = named if name == 'zend_call_function' else args[-1]
        if collection == PARSED and frame.complete and UNREAD_CONTROL not in state.flags and ('N',) not in state.events:
            self.forwarded = True
        return [(ANYV, state)]

    def _initialize_context(self, args: list[Value], state: State) -> list[Outcome]:
        context = pointer(args[0])
        if context is None or not isinstance(args[2], Fn):
            return self.unknown_call(args, state)
        state.write(context.rid, context.path + ('function',), args[2])
        state.write(context.rid, context.path + ('status',), 0)
        handle = state.allocate(SYMBOLIC)
        state.write(handle, ('function',), args[2])
        state.write(context.rid, context.path + ('handle',), Ptr(handle, ()))
        return [(0, state)]

    def _resume_context(self, args: list[Value], execution: tuple[State, Frame]) -> list[Outcome]:
        state, frame = execution
        fiber = pointer(args[0])
        if fiber is None:
            return self.unknown_call(args, state)
        context = self.load(Ptr(fiber.rid, fiber.path + ('previous',)), state)
        if not isinstance(context, Ptr):
            return self.unknown_call(args, state)
        callback = self.load(Ptr(context.rid, context.path + ('function',)), state)
        handle = self.load(Ptr(context.rid, context.path + ('handle',)), state)
        if not isinstance(handle, Ptr) or state.read(handle.rid, ('function',)) != callback:
            return self.unknown_call(args, state)
        state.write('g:executor_globals', ('active_fiber',), fiber)
        state.write('g:executor_globals', ('current_fiber_context',), context)
        transfer = state.allocate(SYMBOLIC)
        state.write(transfer, ('flags',), 0)
        return self.call_value(callback, [Ptr(transfer, ())], state, frame)

    def call_name(self, name: str, args: list[Value], state: State, frame: Frame) -> list[Outcome]:
        if name == PARSE:
            return self._parse_collection(args, state)
        if name in TARGETS and target_api(self.index, (name, frame.source)):
            return self._target_call(name, args, (state, frame))
        if name in SAVE_CONTEXT and not self.index.definitions(name, frame.source):
            return [(0, state)]
        if name in RESTORE_CONTEXT and not self.index.definitions(name, frame.source):
            return []
        return self._source_call(name, args, (state, frame))

    def _source_call(self, name: str, args: list[Value], execution: tuple[State, Frame]) -> list[Outcome]:
        state, frame = execution
        if name == 'strlen' and strlen_api(self.index, frame.source):
            length = literal_length(self.index.program, args[0])
            return [(length, state)] if length is not None else self.unknown_call(args, state)
        if name in ('zend_ini_long', 'zend_ini_string_ex') and self.protocols.ini and source_api(self.index, (name, frame.source), INI_SOURCE):
            if name == 'zend_ini_long' or args[-1] == 0:
                return [(Sym(f'named-extras:ini:{name}:{args!r}'), state)]
        if name in CONTEXT_APIS:
            if not (self.protocols.contexts and source_api(self.index, (name, frame.source), CONTEXT_SOURCE)):
                return self.unknown_call(args, state)
            return self._initialize_context(args, state) if name == 'zend_fiber_init_context' else self._resume_context(args, (state, frame))
        outcomes = super().call_name(name, args, state, frame)
        if name == 'object_init_ex' and self.protocols.objects and source_api(self.index, (name, frame.source), OBJECT_SOURCE):
            return self._initialized_objects(args, outcomes)
        return outcomes

    def _initialized_objects(self, args: list[Value], outcomes: list[Outcome]) -> list[Outcome]:
        destination = pointer(args[0])
        payload = Ptr(destination.rid, destination.path + ('value',)) if destination is not None else None
        expanded = [(status, member) for value, state in outcomes for status, member in self.alts(value, state)]
        for status, member in expanded:
            obj = self.load(payload, member) if status == 0 and payload is not None else ANYV
            if pointer(obj) is not None:
                member.flags = member.flags | {object_label(obj)}
        return expanded


class Forwarding:
    def __init__(self, program: Program) -> None:
        self.program = program
        self.machine: FlowMachine | None = None

    def proves(self, definition: Definition, parsed: ParsedCollection) -> bool:
        if self.machine is None:
            self.machine = FlowMachine(FlowIndex(self.program))
        addresses = [f'&{name}' for name in (*parsed.inputs, parsed.destination)]
        seed = f'{PARSE}({", ".join(addresses)});'
        root = copy(definition)
        root.body = definition.body[:parsed.start] + seed + definition.body[parsed.end:]
        world = World(self.machine.index)
        world.machine = self.machine
        self.machine.forwarded = False
        try:
            self.machine.call(root, list(parsed.parameters), call_state(world), FLOW_BUDGET)
            return self.machine.forwarded
        finally:
            self.machine.index.compiled.pop(id(root), None)
