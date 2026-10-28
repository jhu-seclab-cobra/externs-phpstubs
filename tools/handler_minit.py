"""Class registration stage of the handler extraction (spec-extraction-handlers.md steps 1-3).

The registration functions of every extension run as the engine runs them, over the abstract memory of
``handler_memory``; the result is the frozen state in which each registered class has its class entry
(``create_object``, ``default_object_handlers``) and each handler table holds its final contents. Only the
functions that can reach a handler or creator write, a registration or a table are read; every other call is unknown.
"""

import collections
import re

import php_src
from handler_expr import OFFSET_NAMES
from handler_index import NORETURN, THROWERS, Index
from handler_machine import Machine
from handler_memory import State, join_states
from handler_world import World

CALL_NAME = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
SUB_MINIT = re.compile(r"PHP_MINIT\((\w+)\)")
KEYWORDS = {"if", "while", "for", "switch", "return", "sizeof", "defined", "do", "else", "case"}
# A write of a field the creation stage follows: the handler table of an object, or the creator and default table
# of a class entry.
FIELD_WRITE = re.compile(r"(?:->|\.)\s*(?:handlers|default_object_handlers|create_object)\s*=(?!=)")
# A function can write a slot of a table through a pointer only when its text names the table type or a handlers field.
HOLDS_TABLE = re.compile(r"\bzend_object_handlers\b|\bhandlers\b")
REGISTRATION_START = "zend_register_default_classes"
MODULE_START = "zm_startup_"
MINIT_BUDGET = 400_000


class Policy:
    """Which called functions the machine reads, which statements it cannot read matter, and which calls may write
    through their pointer arguments."""

    def __init__(self, interpreted, relevant, unread_writes=False):
        self.interpreted, self.relevant, self.unread = interpreted, relevant, unread_writes

    def interpret(self, definition):
        return id(definition) in self.interpreted

    def opaque(self, definition, text):
        return self.relevant(definition, text)

    def unread_writes(self, pointer):
        return self.unread


def reaching(definitions, seeds):
    """The seeds and every definition that calls one of them, directly or through other callers."""
    callers = collections.defaultdict(list)
    for definition in definitions:
        for name in set(CALL_NAME.findall(definition.body)):
            callers[name].append(definition)
    found, work = {id(d) for d in seeds}, list(seeds)
    while work:
        for caller in callers.get(work.pop().name, ()):
            if id(caller) not in found:
                found.add(id(caller))
                work.append(caller)
    return found


class Registered:
    """The registration stage of one checkout: machine, index and the frozen state after the registrations."""

    def __init__(self, program):
        self.program, self.index = program, Index(program)
        self.definitions = [d for ds in program.functions.values() for d in ds if not d.is_macro]
        self.machine = Machine(self.index, None)
        self.world = World(self.index)
        self.world.machine = self.machine
        self.state = State(self.world)
        self.registered = self.register()

    def register(self):
        """Run every registration function; the classes registered are the class regions of the state."""
        relevant = self.relevance()
        seeds = [d for d in self.definitions if relevant(d, d.body)]
        policy = Policy(reaching(self.definitions, seeds), relevant)
        self.machine.policy = policy
        roots = self.roots(policy)
        for definition in roots + roots:
            self.start(definition)
        self.reject_unread(policy)
        return sorted(r[2:] for r in {**self.state.base, **self.state.mem} if r.startswith("c:"))

    def relevance(self):
        """The test of a statement text of one function: whether it is a class registration call, a write of a class
        entry field, a handler slot written through a pointer of a function that holds a table, or a table assigned or
        copied into by name."""
        names = "|".join(map(re.escape, self.index.tables))
        fields = "|".join(map(re.escape, self.index.fields))
        plain = re.compile(
            r"(?:->|\.)\s*(?:default_object_handlers|create_object)\s*=(?!=)"
            r"|zend_register_internal_(?:class|interface|enum)|INIT(?:_NS)?_CLASS_ENTRY|register_class_\w+"
            rf"|\b(?:{names})\b\s*(?:\.\s*\w+\s*)?=(?!=)"
            rf"|\b(?:memcpy|memmove|memset)\s*\(\s*&?\s*(?:{names})\b"
        )
        slots = re.compile(rf"(?:->|\.)\s*(?:{fields})\s*=(?!=)")
        return lambda definition, text: bool(
            plain.search(text) or (slots.search(text) and HOLDS_TABLE.search(definition.body))
        )

    def roots(self, policy):
        """The registration entry points in a fixed order: the default classes, then every module startup that no
        other startup invokes."""
        functions = self.program.functions
        invoked = {name for d in self.definitions if policy.interpret(d) for name in SUB_MINIT.findall(d.body)}
        starts = sorted(
            (d for name, ds in functions.items() if name.startswith(MODULE_START) for d in ds),
            key=lambda d: (d.name, d.source.relative),
        )
        defaults = list(functions.get(REGISTRATION_START, ()))
        return [d for d in defaults + starts if policy.interpret(d) and d.name[len(MODULE_START):] not in invoked]

    def start(self, definition):
        arguments = [1, 0][:len(definition.params)]
        exits, complete = self.machine.call(definition, arguments, self.state, MINIT_BUDGET)
        finished = [s for v, s in exits if v == 0 or not isinstance(v, int)]
        if finished:
            self.state = join_states(finished) if len(finished) > 1 else finished[0]
        self.state.freeze()

    def reject_unread(self, policy):
        """A statement of a registration function that the machine cannot read, and that touches a handler or
        creator, leaves the registered tables unproven: the extraction fails instead of guessing."""
        if self.machine.opaques:
            definition, text = self.machine.opaques[0]
            raise php_src.ExtractionFailure(
                f"{definition.source.relative}: {definition.name}: unreadable statement in a class registration: "
                f"{text.strip()[:80]!r}"
            )


def is_primitive(machine, name):
    return hasattr(machine, "p_" + name) or bool(THROWERS.fullmatch(name)) or name in NORETURN


def pure_functions(machine, definitions, excluded):
    """The definitions that call only each other, primitives and keywords: they cannot reach a write the creation
    stage follows, and their results matter to it (a helper that converts an object to its struct)."""
    callees = {id(d): set(CALL_NAME.findall(d.body)) - KEYWORDS - OFFSET_NAMES for d in definitions}
    pure, names, grown = set(), set(), True
    while grown:
        grown = False
        for definition in definitions:
            if id(definition) in pure or id(definition) in excluded:
                continue
            if all(n in names or is_primitive(machine, n) for n in callees[id(definition)]):
                pure.add(id(definition))
                names.add(definition.name)
                grown = True
    return pure
