"""Request summaries of the handler extraction (spec-extraction-handlers.md steps 4-6).

One handler function runs on the engine's arguments for one request: the object, the output zval, the operands. The
exits that return success without a pending exception are the normal exits; the type tag the function left in the
output zval classifies each of them. The relative order of the user-method call and the native writes to the output on
the paths of a string conversion gives its dispatch order.
"""

import collections
import re

import php_src
from handler_expr import masked
from handler_memory import ANYV, Agg, Alt, Fill, Fn, METHOD_SYMBOLS, Masked, Ptr, Region, Sym, Test, SYMBOLIC, alternatives, origin
from handler_machine import CALL_SLICE, Exhausted
from handler_minit import Policy
from php_src_c.definitions import CompleteSummary, ProcedureSummaries
from handler_prims import EXCEPTION, EXCEPTIONS_REGION
from handler_values import resolve

SUMMARY_BUDGET = 1_000_000
DIAGNOSTICS = re.compile(r"zend_error\w*|php_error_docref\w*|zend_get_executed_\w+|php_verror|zend_message_dispatcher|zend_output_debug_string")
SELF, CLASS, OUT, FIRST, SECOND = "o:self", "o:ce", "o:out", "o:op1", "o:op2"
OPERAND_SYMBOLS = "o:op"
TYPE_INFO = ("u1", "type_info")
TYPE_MASK = 0xFF
UNWRITTEN = 0
SUCCESS = 0
UNARY = {"ZEND_BW_NOT", "ZEND_BOOL_NOT"}
METHOD = Fn("__toString", None)
STRING_TAG = "IS_STRING"
KINDS = {"IS_STRING": "str", "IS_LONG": "num", "IS_DOUBLE": "num", "IS_TRUE": "bool", "IS_FALSE": "bool"}
NATIVE, METHOD_EVENT = ("N",), ("M",)


class SummaryPolicy(Policy):
    """The policy of a summary run: every function body the machine can read is read, except the engine's error
    reporting, which cannot change what a handler returns or writes."""

    def __init__(self):
        super().__init__((), lambda definition, text: True, unread_writes=True)

    def interpret(self, definition):
        return not DIAGNOSTICS.fullmatch(definition.name)


class Summary:
    """The outcome of one request on one handler: the normal result kinds (None when the proof is incomplete), the
    string dispatch order of a string conversion, and the reason a fact is left unestablished."""

    def __init__(self, results=None, dispatch=None, reason=None):
        self.results, self.dispatch, self.reason = results, dispatch, reason


class Summarizer:
    """Summaries of handler functions over the frozen registration state of one checkout."""

    def __init__(self, registered):
        self.registered, self.machine = registered, registered.machine
        self.program, self.index = registered.program, registered.index
        self.policy = SummaryPolicy()
        self.tags = self.index.tags
        if not self.tags:
            raise php_src.ExtractionFailure("no value tag header in the checkout")
        self.procedures = HandlerProcedures(self.machine)

    def cast(self, function, tag, has_method):
        """The summary of ``cast_object`` of a class with or without an effective ``__toString`` for one tag."""
        return self.summarize(function, "cast", tag, has_method)

    def operation(self, function, opcode):
        return self.summarize(function, "operation", opcode, False)

    def compare(self, function):
        return self.summarize(function, "compare", None, False)

    def summarize(self, function, slot, request, has_method):
        definitions = self.definitions(function)
        if not definitions:
            return Summary(reason=f"no readable definition of {function.name}")
        machine = self.machine
        machine.policy, machine.sites, machine.marker = self.policy, None, METHOD if has_method else None
        machine.opaques.clear()
        self.procedures.request = slot
        exits, previous = [], machine.procedures
        machine.procedures = self.procedures
        try:
            for definition in definitions:
                state, arguments = self.setup(definition, slot, request, has_method)
                if arguments is None:
                    return Summary(reason=f"unknown request {request}")
                found, complete = machine.call(definition, arguments, state, SUMMARY_BUDGET)
                if not complete:
                    return Summary(reason=f"{definition.name}: incomplete run")
                exits.extend(found)
        finally:
            machine.procedures = previous
        return self.classify(exits, slot, request)

    def definitions(self, function):
        return [d for d in self.program.functions.get(function.name, ())
                if not d.is_macro and (function.source is None or d.source.relative == function.source)]

    # -- the request ---------------------------------------------------------------------------------------------
    def setup(self, definition, slot, request, has_method):
        state = self.registered.state.fork()
        state.watch = frozenset({OUT}) if request == STRING_TAG and has_method else frozenset()
        state.put(SELF, Region(SYMBOLIC, {("ce",): Ptr(CLASS, ())}, owner=state.token))
        state.put(CLASS, Region(SYMBOLIC, {("__tostring",): METHOD if has_method else 0}, owner=state.token))
        state.put(OUT, Region(ANYV, {TYPE_INFO: 0}, owner=state.token))
        for rid in (FIRST, SECOND):
            state.put(rid, Region(SYMBOLIC, owner=state.token))
        return state, self.arguments(definition, slot, request)

    def arguments(self, definition, slot, request):
        out, first, second = Ptr(OUT, ()), Ptr(FIRST, ()), Ptr(SECOND, ())
        if slot == "compare":
            return [first, second]
        if slot == "cast":
            tag = self.tags.get(request)
            return None if tag is None else [Ptr(SELF, ()), out, tag]
        opcode = self.index.constant(request, definition.source)
        if opcode is None:
            return None
        return [opcode, out, first, 0 if request in UNARY else second]

    # -- the exits -----------------------------------------------------------------------------------------------
    def classify(self, exits, slot, request):
        events = [state.events for _, state in exits]
        dispatch = self.dispatch(events) if request == STRING_TAG else None
        if slot == "compare":
            return self.compare_summary(exits, dispatch)
        kinds = set()
        for value, state in exits:
            normal = self.normal(value, state)
            if normal is None:
                return Summary(dispatch=dispatch, reason="the return value or the exception state is unknown")
            if normal:
                found = self.kinds(state)
                if found is None:
                    return Summary(dispatch=dispatch, reason="the output type is unknown")
                kinds |= found
        return Summary(frozenset(kinds), dispatch)

    def compare_summary(self, exits, dispatch):
        pending = [exception_values(state) for _, state in exits]
        if None in pending:
            return Summary(dispatch=dispatch, reason="the exception state is unknown")
        return Summary(frozenset({"num"}) if any(0 in flags for flags in pending) else frozenset(), dispatch)

    def normal(self, value, state):
        """True when some path of the exit returns success with no pending exception, False when none does, None when
        the return value or the exception flag is unknown."""
        flags = exception_values(state)
        if flags is None or 0 not in flags:
            return None if flags is None else False
        values = [resolve(v, state) for v, _ in alternatives(value)]
        return SUCCESS in values if all(isinstance(v, int) for v in values) else None

    def kinds(self, state):
        """The result kinds of the output zval of a normal exit, or None when one of its types is unknown. An output
        no path wrote is unestablished; an unwritten alternative beside proved writes belongs to a failure path."""
        items = [item for item, _ in alternatives(state.read(OUT, TYPE_INFO))]
        found = {self.alternative_kind(item, state) for item in items if item != UNWRITTEN}
        return found if found and None not in found else None

    def alternative_kind(self, item, state):
        """The kind one alternative of the output type tag stands for: a known tag by its name, a value derived from
        the user method or an operand, as ``any``; None for an unresolved type or any other symbol."""
        tag = resolve(masked(item, TYPE_MASK), state)
        if isinstance(tag, int):
            name = self.tag_name(tag)
            return KINDS.get(name, "any") if name is not None else None
        if tag is ANYV:
            return None
        root = origin(tag)
        return "any" if root is not None and root.startswith(("m:", OPERAND_SYMBOLS)) else None

    def tag_name(self, value):
        return next((name for name, number in self.tags.items() if number == value and not name.startswith("_")), None)

    @staticmethod
    def dispatch(histories):
        """The order of the user-method call (M) and the native writes to the output (N) over the exits of a run."""
        if any(h.index(NATIVE) < h.index(METHOD_EVENT) for h in histories if NATIVE in h and METHOD_EVENT in h):
            return "native_first"
        if any(METHOD_EVENT in h and NATIVE in h for h in histories):
            return "method_first"
        return "method_only" if any(METHOD_EVENT in h for h in histories) else "none"


def exception_values(state):
    """The known pending-exception alternatives, or None when one is unresolved."""
    flags = [resolve(value, state) for value, _ in alternatives(state.read(EXCEPTIONS_REGION, EXCEPTION))]
    return set(flags) if all(isinstance(flag, int) for flag in flags) else None


def frozen_value(value):
    if isinstance(value, (dict, Agg)):
        return frozenset((key, frozen_value(item)) for key, item in value.items())
    if isinstance(value, Alt):
        return Alt(tuple((frozen_value(item), guards) for item, guards in value.items))
    return value


class ProcedureOutcome:
    """A handler-domain procedure summary: return values with memory effects, and proof completeness."""

    def __init__(self, exits=(), complete=True):
        self.exits, self.complete = list(exits), complete

    def __eq__(self, other):
        return self.complete == other.complete and self.key() == other.key()

    def key(self):
        return frozenset((frozen_value(value), state.key(), state.tags) for value, state in self.exits)


def join_outcomes(old, fresh):
    if not old.complete or not fresh.complete:
        return ProcedureOutcome(complete=False)
    exits = {(frozen_value(value), state.key(), state.tags): (value, state)
             for value, state in old.exits + fresh.exits}
    return ProcedureOutcome(exits.values(), old.complete and fresh.complete)


def pointer_regions(value):
    if isinstance(value, Ptr):
        return [value.rid]
    if isinstance(value, Sym):
        return [value.pointer().rid]
    if isinstance(value, (Fill, Masked, Test)):
        return pointer_regions(value[0])
    if isinstance(value, Alt):
        return [rid for item, _ in value.items for rid in pointer_regions(item)]
    if isinstance(value, (dict, Agg)):
        return [rid for item in value.values() for rid in pointer_regions(item)]
    return []


def symbol_source(rid):
    while rid.startswith("y:"):
        rid = rid[2:]
    return rid


def reachable_symbol(sid, regions):
    source = symbol_source(sid)
    return source.startswith(("g:", "c:")) or any(
        source == symbol_source(rid) or source.startswith(symbol_source(rid) + "/") for rid in regions)


def mapped_symbol(sid, mapping):
    target = mapping.get("y:" + sid)
    if target is not None and target.startswith("y:"):
        return target[2:]
    for source, target in mapping.items():
        if sid == source or sid.startswith(source + "/"):
            return target + sid[len(source):]
    return "y:" + mapped_symbol(sid[2:], mapping) if sid.startswith("y:") else sid


def mapped_region(rid, mapping):
    if rid in mapping:
        return mapping[rid]
    return "y:" + mapped_symbol(rid[2:], mapping) if rid.startswith("y:") else rid


def argument_region(rid, index):
    source = symbol_source(rid)
    prefix = OPERAND_SYMBOLS + ":p" if source.startswith(OPERAND_SYMBOLS) else (
        METHOD_SYMBOLS + "p" if source.startswith(METHOD_SYMBOLS) else "p:")
    return ("y:" if rid.startswith("y:") else "") + prefix + str(index)


def symbol_location(sid):
    parent, separator, path = sid.rpartition("/")
    if not separator:
        return None
    parts = path.partition("#")[0].split(".") if path else []
    return parent, tuple(int(part) if part.lstrip("-").isdigit() else part for part in parts)


class ProcedureInput:
    """The definition, arguments and captured state of one procedure input."""

    def __init__(self, definition, args, state):
        self.definition, self.args, self.state = definition, args, state


class HandlerProcedures:
    """The memory-effect domain of the shared procedure-summary driver, over one registration state.

    Caller locals outside the argument closure are absent from an input. Reachable local/heap regions are renamed
    by argument position, preserving aliases; cached effects are renamed back and applied to the current caller.
    """

    def __init__(self, machine):
        self.machine, self.inputs, self.request, self.root = machine, {}, None, None
        self.driver = ProcedureSummaries(self._evaluate, ProcedureOutcome(), join_outcomes,
                                         closed=lambda outcome: not outcome.complete)

    def _value(self, value, mapping):
        if isinstance(value, Ptr):
            return Ptr(mapped_region(value.rid, mapping), value.path)
        if isinstance(value, Sym):
            return Sym(mapped_symbol(value.sid, mapping))
        if isinstance(value, (Fill, Masked, Test)):
            return type(value)(self._value(value[0], mapping), *value[1:])
        if isinstance(value, Alt):
            return Alt(tuple((self._value(item, mapping), guards) for item, guards in value.items))
        if isinstance(value, (dict, Agg)):
            return Agg({path: self._value(item, mapping) for path, item in value.items()})
        return value

    def _region(self, region, mapping, token):
        return Region(self._value(region.base, mapping),
                      {path: self._value(value, mapping) for path, value in region.cells.items()}, token, region.kind)

    @staticmethod
    def _changed(state, rid, region):
        original = state.base.get(rid) or state.world.initial(rid)
        return original is None or original.fingerprint() != region.fingerprint()

    def _closure(self, args, state):
        roots = [rid for arg in args for rid in pointer_regions(arg)]
        roots += sorted(rid for rid, region in state.mem.items()
                        if rid.startswith(("g:", "c:")) and self._changed(state, rid, region))
        retained, mapping = {}, {}
        frontier = collections.deque(roots)
        while frontier:
            rid = frontier.popleft()
            if rid in retained:
                continue
            region = state.region(rid)
            retained[rid] = region
            if rid.startswith(("l:", "h:", "p:", "y:", OPERAND_SYMBOLS + ":p", METHOD_SYMBOLS + "p")) and rid not in state.base:
                mapping[rid] = argument_region(rid, len(mapping))
            if region is not None:
                frontier.extend(found for value in (region.base, *region.cells.values()) for found in pointer_regions(value))
                frontier.extend(other for other in state.mem if other.startswith("y:")
                                and symbol_source(other).startswith(symbol_source(rid) + "/"))
        return retained, mapping

    def _capture(self, args, state):
        args = [resolve(arg, state) for arg in args]
        retained, mapping = self._closure(args, state)
        captured = state.fork()
        captured.mem = {mapped_region(rid, mapping): self._region(region, mapping, captured.token)
                        for rid, region in retained.items() if region is not None and self._changed(state, rid, region)}
        captured.prints, captured.serial = {}, 0
        self._materialize(captured, state, (retained, mapping))
        captured.facts = {(mapped_symbol(sid, mapping), mask): fact for (sid, mask), fact in state.facts.items()
                          if reachable_symbol(sid, retained)}
        captured.events = tuple(dict.fromkeys(state.events))
        captured.watch = frozenset(mapped_region(rid, mapping) for rid in state.watch)
        return [self._value(arg, mapping) for arg in args], captured, mapping

    def _materialize(self, captured, state, projection):
        retained, mapping = projection
        for rid in mapping:
            location = symbol_location(rid[2:]) if rid.startswith("y:") else None
            if location is None:
                continue
            parent, path = location
            if parent not in retained and not parent.startswith(("g:", "c:")):
                continue
            value = state.read(parent, path)
            if not isinstance(value, Sym) or value.sid != rid[2:]:
                continue
            target = mapped_region(parent, mapping)
            if target not in captured.mem:
                captured.put(target, self._region(state.region(parent), mapping, captured.token))
            captured.writable(target).cells[path] = self._value(value, mapping)

    def _admit(self, definition, args, state):
        args, captured, mapping = self._capture(args, state)
        key = (id(definition), tuple(map(frozen_value, args)), captured.key(), captured.tags, captured.watch)
        self.inputs.setdefault(key, ProcedureInput(definition, args, captured))
        return key, mapping

    def solve(self, definition, args, state):
        key, mapping = self._admit(definition, args, state)
        if self.request == "compare":
            projected = ("compare", key)
            self.inputs.setdefault(projected, self.inputs[key])
            key = projected
        self.root = key
        self.driver.solve([key])
        outcome = self.driver.summaries[key]
        exits = self._restore(outcome, self.inputs[key].state, mapping, state)
        self.inputs = {node: data for node, data in self.inputs.items() if node in self.driver.summaries}
        return exits, outcome.complete

    def read(self, definition, args, state):
        key, mapping = self._admit(definition, args, state)
        outcome = self.driver.read(key, eager=True)
        if not outcome.complete:
            return self.machine.unknown_call(args, state)
        return self._restore(outcome, self.inputs[key].state, mapping, state)

    def close(self, frame, exits):
        if self.driver.current != self.root or self.request != "compare" or not frame.complete:
            return
        normal = [(value, member) for value, member in exits
                  if (flags := exception_values(member)) is not None and 0 in flags]
        if normal:
            for _, member in normal:
                frame.release(member)
            raise CompleteSummary(self.root, ProcedureOutcome(normal))

    def _evaluate(self, key, driver):
        entry = self.inputs[key]
        start = self.machine.steps
        saved, owner = self.machine.limit, self.machine.owner
        token = object()
        if key != self.root and start + CALL_SLICE < saved:
            self.machine.limit, self.machine.owner = start + CALL_SLICE, token
        try:
            try:
                exits, complete = self.machine.run(entry.definition, entry.args, entry.state.fork(), 0)
            except Exhausted as exhausted:
                if exhausted.owner is not token:
                    raise
                self.machine.steps = start
                return ProcedureOutcome(complete=False)
        finally:
            self.machine.limit, self.machine.owner = saved, owner
        for _, member in exits:
            member.events = tuple(dict.fromkeys(member.events))
            for rid in list(member.mem):
                if not self._changed(member, rid, member.mem[rid]):
                    member.drop(rid)
        return ProcedureOutcome(exits, complete)

    def _restore(self, outcome, before, mapping, caller):
        exits = []
        for value, member in outcome.exits:
            restored = caller.fork()
            inverse = {target: source for source, target in mapping.items()}
            for rid, region in member.mem.items():
                if rid.startswith("h:") and rid not in before.mem and rid not in before.base:
                    inverse[rid] = restored.allocate(region.base, region.kind)
            self._effects(before, member, restored, inverse)
            exits.append((self._value(value, inverse), restored))
        return exits

    def _effects(self, before, member, restored, inverse):
        for rid, region in member.mem.items():
            original = before.mem.get(rid) or before.base.get(rid) or before.world.initial(rid)
            if original is None or original.fingerprint() != region.fingerprint():
                restored.put(mapped_region(rid, inverse), self._region(region, inverse, restored.token))
        restored.tags, restored.events, restored.flags = member.tags, member.events, member.flags
        restored.facts.update({(mapped_symbol(sid, inverse), mask): fact for (sid, mask), fact in member.facts.items()})
        restored.serial = max(restored.serial, member.serial)

    def abort(self):
        pending = set(self.driver.pending)
        self.driver.abort()
        for key in pending:
            self.inputs.pop(key, None)
