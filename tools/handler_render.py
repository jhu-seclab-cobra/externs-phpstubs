"""The handler tables of a class signature as the models document spells them (commons-phpmodels handler types).

``Target``, ``Fact`` and ``Table`` hold the values of one emitted table; ``render_handlers`` spells the ``handlers``
field of a signature in the layout the models documents use.
"""

import re

RESULT_ORDER = ("str", "num", "bool", "any")
QUOTED = re.compile(r": | #|^[^A-Za-z0-9_./]")


class Target:
    """One handler function that can serve a request: its source-qualified symbol, the normal result kinds, and the
    string dispatch order of a string request."""

    def __init__(self, symbol, results, dispatch=None):
        self.symbol, self.results, self.dispatch = symbol, frozenset(results), dispatch


class Fact:
    """One slot of a table, for one request (None for the whole slot and for a comparison): present with targets, or
    positively absent."""

    def __init__(self, slot, request=None, targets=(), absent=False):
        self.slot, self.request, self.targets, self.absent = slot, request, list(targets), absent


class Table:
    """One effective handler table alternative: the identifier of its source and the facts established for it."""

    def __init__(self, identifier, facts=()):
        self.identifier, self.facts = identifier, list(facts)


def scalar(text):
    return f'"{text}"' if QUOTED.search(text) else text


def render_target(target):
    lines = [f"              - symbol: {scalar(target.symbol)}"]
    results = ", ".join(kind for kind in RESULT_ORDER if kind in target.results)
    lines.append(f"                results: [{results}]")
    if target.dispatch:
        lines.append(f"                stringDispatch: {target.dispatch}")
    return lines


def render_fact(fact):
    lines = [f"          - slot: {fact.slot}"]
    if fact.request:
        lines.append(f"            request: {fact.request}")
    if fact.absent:
        lines.append("            absent: true")
        return lines
    lines.append("            targets:")
    for target in fact.targets:
        lines.extend(render_target(target))
    return lines


def render_table(table):
    lines = [f"      - id: {scalar(table.identifier)}"]
    if not table.facts:
        return lines + ["        facts: []"]
    lines.append("        facts:")
    for fact in table.facts:
        lines.extend(render_fact(fact))
    return lines


def render_handlers(tables):
    """The ``handlers`` field lines of a signature; empty when a class has no table."""
    if not tables:
        return ""
    lines = ["    handlers:"]
    for table in tables:
        lines.extend(render_table(table))
    return "\n".join(lines) + "\n"
