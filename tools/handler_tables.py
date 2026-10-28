"""Effective handler tables of one class (spec-extraction-handlers.md steps 2, 4 and 5).

The slots of a table in the frozen registration state are read for every source configuration: a slot assigned under
``#if`` holds alternatives with their conditions. The configurations that give a table the same contents are one
table alternative; alternatives of one symbol get a branch suffix on their identifier. Each present slot is summarized
for every consumed request; a request whose summary is incomplete is omitted, never emitted empty.
"""

import collections
import itertools
import re

import php_src
from handler_memory import Fn, alternatives
from handler_render import Fact, Table, Target

SLOTS = (("cast", "cast_object"), ("compare", "compare"), ("operation", "do_operation"))
STRING_REQUEST = "IS_STRING"
CONFIGURATION_CAP = 6
SPELLED = re.compile(r"!?defined\(\w+\)")


class Report:
    """What the extraction left unestablished and how each handler write site was accounted for."""

    def __init__(self):
        self.omitted, self.dispositions = [], []

    def omit(self, table, slot, request, reason):
        self.omitted.append((table, slot, request, reason))


def atom_of(literal):
    """A condition literal as its atom and polarity: ``!defined(X)`` is (``defined(X)``, False)."""
    text = literal.strip()
    return (text[1:].strip(), False) if text.startswith("!") else (text, True)


def spelled(atom, truth):
    return atom if truth else "!" + atom


def holds(conditions, configuration):
    return all(configuration[atom] == truth for atom, truth in map(atom_of, conditions))


def slot_values(value, configuration):
    """The values a slot can hold under one configuration: the alternatives whose conditions hold, else the
    unconditional ones."""
    items = alternatives(value)
    conditioned = [item for item, conditions in items if conditions and holds(conditions, configuration)]
    return conditioned or [item for item, conditions in items if not conditions]


def configurations(values):
    """The truth assignments over the condition atoms of the slot values of a table."""
    atoms = sorted({atom_of(c)[0] for value in values for _, conditions in alternatives(value) for c in conditions})
    if len(atoms) > CONFIGURATION_CAP:
        raise php_src.ExtractionFailure(f"a handler table depends on {len(atoms)} source conditions: {atoms}")
    return [dict(zip(atoms, truths)) for truths in itertools.product((True, False), repeat=len(atoms))]


def contents(slots, configuration):
    """The contents a table has under one configuration: one value choice per slot; each combination of choices is a
    distinct alternative."""
    names = [name for name, _ in SLOTS]
    choices = [slot_values(slots[name], configuration) for name in names]
    return [dict(zip(names, chosen)) for chosen in itertools.product(*choices)]


def variants(slots):
    """The (suffix, contents) alternatives of a table whose slots hold the given values: configurations with equal
    contents are one alternative; the suffix is None when the table has one."""
    groups = collections.OrderedDict()
    for configuration in configurations(slots.values()):
        for found in contents(slots, configuration):
            key = tuple(found[name] for name, _ in SLOTS)
            groups.setdefault(key, []).append(configuration)
    if len(groups) == 1:
        return [(None, dict(zip((n for n, _ in SLOTS), next(iter(groups)))))]
    suffixes = suffixes_of(list(groups.values()))
    return [(suffix, dict(zip((n for n, _ in SLOTS), key))) for suffix, key in zip(suffixes, groups)]


def suffixes_of(groups):
    """One identifier suffix per group of configurations: the literals all its configurations share, when the group
    is exactly the configurations those literals select and the literals tell the groups apart; else its ordinal."""
    spelling = [shared_literals(group) for group in groups]
    if all(s is not None for s in spelling) and len(set(spelling)) == len(spelling):
        return spelling
    return [str(number) for number in range(1, len(groups) + 1)]


def shared_literals(group):
    atoms = sorted(group[0])
    shared = [(a, group[0][a]) for a in atoms if all(c[a] == group[0][a] for c in group)]
    free = len(atoms) - len(shared)
    literals = [spelled(a, t) for a, t in shared]
    if len(group) != 2 ** free or not literals or not all(SPELLED.fullmatch(lit) for lit in literals):
        return None
    return " && ".join(literals)


class TableBuilder:
    """Facts of the tables of classes over one registration state, one summarizer and the consumed requests."""

    def __init__(self, registered, summarizer, requests, report):
        self.state, self.summarizer, self.report = registered.state, summarizer, report
        self.casts, self.operations = sorted(requests[0]), sorted(requests[1])

    def tables(self, table, has_method):
        """The table alternatives of one handler table for a class with or without an effective string method."""
        if table.region is None:
            self.report.omit(table.identity, None, None, "no rule resolves the table")
            return [Table(table.identity)]
        slots = {name: self.state.read(table.region, (field,)) for name, field in SLOTS}
        found = variants(slots)
        return [self.table(table.identity, suffix, contents, has_method) for suffix, contents in found]

    def table(self, identity, suffix, contents, has_method):
        identifier = identity if suffix is None else f"{identity} #{suffix}"
        facts = []
        for slot, _ in SLOTS:
            facts.extend(self.slot_facts(identifier, slot, contents[slot], has_method))
        return Table(identifier, facts)

    def slot_facts(self, identifier, slot, value, has_method):
        if isinstance(value, int) and value == 0:
            return [Fact(slot, absent=True)]
        if not isinstance(value, Fn) or value.source is None:
            self.report.omit(identifier, slot, None, "the slot holds a value no rule resolves")
            return []
        if slot == "compare":
            return self.requested(identifier, slot, None, value, has_method)
        names = self.casts if slot == "cast" else self.operations
        return [fact for name in names for fact in self.requested(identifier, slot, name, value, has_method)]

    def requested(self, identifier, slot, name, function, has_method):
        summary = self.summary(slot, name, function, has_method)
        dispatch = summary.dispatch
        if name == STRING_REQUEST and summary.results is not None:
            dispatch = self.summarizer.cast(function, name, True).dispatch
        if summary.results is None or (name == STRING_REQUEST and dispatch is None):
            self.report.omit(identifier, slot, name, summary.reason)
            return []
        target = Target(f"{function.source}:{function.name}", summary.results, dispatch if name == STRING_REQUEST else None)
        return [Fact(slot, name.lower() if name else None, [target])]

    def summary(self, slot, name, function, has_method):
        if slot == "cast":
            return self.summarizer.cast(function, name, has_method)
        if slot == "operation":
            return self.summarizer.operation(function, name)
        return self.summarizer.compare(function)
