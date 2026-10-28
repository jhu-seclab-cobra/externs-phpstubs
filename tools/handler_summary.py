"""Request summaries of the handler extraction (spec-extraction-handlers.md steps 4-6).

One handler function runs on the engine's arguments for one request: the object, the output zval, the operands. The
exits that return success without a pending exception are the normal exits; the type tag the function left in the
output zval classifies each of them. The relative order of the user-method call and the native writes to the output on
the paths of a string conversion gives its dispatch order.
"""

import re

import php_src
from handler_expr import masked
from handler_memory import ANYV, Fn, Ptr, Region, SYMBOLIC, alternatives, origin
from handler_minit import Policy
from handler_prims import EXCEPTION, EXCEPTIONS_REGION
from handler_values import resolve

SUMMARY_BUDGET = 1_000_000
DIAGNOSTICS = re.compile(r"zend_error\w*|php_error_docref\w*|zend_get_executed_\w+|php_verror|zend_message_dispatcher")
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
        self.cache = {}

    def cast(self, function, tag, has_method):
        """The summary of ``cast_object`` of a class with or without an effective ``__toString`` for one tag."""
        key = (function, "cast", tag, has_method if tag == STRING_TAG else False)
        if key not in self.cache:
            self.cache[key] = self.summarize(function, "cast", tag, has_method)
        return self.cache[key]

    def operation(self, function, opcode):
        key = (function, "operation", opcode, False)
        if key not in self.cache:
            self.cache[key] = self.summarize(function, "operation", opcode, False)
        return self.cache[key]

    def compare(self, function):
        key = (function, "compare", None, False)
        if key not in self.cache:
            self.cache[key] = self.summarize(function, "compare", None, False)
        return self.cache[key]

    def summarize(self, function, slot, request, has_method):
        definition = self.definition(function)
        if definition is None:
            return Summary(reason=f"no readable definition of {function.name}")
        state, arguments = self.setup(definition, slot, request, has_method)
        if arguments is None:
            return Summary(reason=f"unknown request {request}")
        machine = self.machine
        machine.policy, machine.sites, machine.marker = self.policy, None, METHOD if has_method else None
        machine.opaques.clear()
        exits, complete = machine.call(definition, arguments, state, SUMMARY_BUDGET)
        if not complete:
            return Summary(reason=f"{definition.name}: incomplete run")
        return self.classify(exits, slot, request)

    def definition(self, function):
        found = [d for d in self.program.functions.get(function.name, ())
                 if not d.is_macro and (function.source is None or d.source.relative == function.source)]
        return found[0] if found else None

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
        pending = [self.exception(state) for _, state in exits]
        if None in pending:
            return Summary(dispatch=dispatch, reason="the exception state is unknown")
        return Summary(frozenset({"num"}) if any(0 in flags for flags in pending) else frozenset(), dispatch)

    def exception(self, state):
        """The pending-exception flag values of an exit: a set of integers, or None when one is unknown."""
        flags = [resolve(v, state) for v, _ in alternatives(state.read(EXCEPTIONS_REGION, EXCEPTION))]
        return set(flags) if all(isinstance(f, int) for f in flags) else None

    def normal(self, value, state):
        """True when some path of the exit returns success with no pending exception, False when none does, None when
        the return value or the exception flag is unknown."""
        flags = self.exception(state)
        if flags is None or 0 not in flags:
            return None if flags is None else False
        values = [resolve(v, state) for v, _ in alternatives(value)]
        return SUCCESS in values if all(isinstance(v, int) for v in values) else None

    def kinds(self, state):
        """The result kinds of the output zval of a normal exit, or None when one of its types is unknown. An output
        no path wrote has the kind ``any``; the unwritten alternative of a joined output belongs to a failure path."""
        items = [item for item, _ in alternatives(state.read(OUT, TYPE_INFO))]
        found = {self.alternative_kind(item, state) for item in items if item != UNWRITTEN} or {"any"}
        return None if None in found else found

    def alternative_kind(self, item, state):
        """The kind one alternative of the output type tag stands for: a known tag by its name, a value derived from
        the user method or an operand, or an unknown value of a complete run, as ``any``; None for any other symbol."""
        tag = resolve(masked(item, TYPE_MASK), state)
        if isinstance(tag, int):
            return KINDS.get(self.tag_name(tag), "any")
        if tag is ANYV:
            return "any"
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
