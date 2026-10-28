"""Admission of lexical bindings before the shared C compiler flattens blocks."""

from dataclasses import dataclass, replace
from typing import TypeAlias

from named_extras_reception import CValue

Declarator: TypeAlias = tuple[str, int, list[CValue], CValue]


@dataclass(frozen=True)
class BindingContext:
    enclosing: frozenset[str]
    local: frozenset[str]


@dataclass(frozen=True)
class BindingFacts:
    local: frozenset[str] = frozenset()
    declared: frozenset[str] = frozenset()
    unresolved: frozenset[str] = frozenset()
    shadowed: frozenset[str] = frozenset()


def syntax_children(value: CValue) -> list[CValue]:
    match value:
        case ('decl', _, list() as entries):
            return [expression for _, _, dimensions, initial in entries for expression in (*dimensions, initial)]
        case ('cast', _, expression):
            return [expression]
        case ('sizeof', _):
            return []
        case ('init', list() as items):
            return [expression for _, expression, _ in items]
    return list(value) if isinstance(value, (tuple, list)) else []


def lexical_scope(value: CValue) -> bool:
    match value:
        case ('block', list()) | ('for', _, _, _, _):
            return True
    return False


def merge_facts(left: BindingFacts, right: BindingFacts) -> BindingFacts:
    return BindingFacts(left.local | right.local, left.declared | right.declared,
                        left.unresolved | right.unresolved, left.shadowed | right.shadowed)


def sequence_facts(values: list[CValue], context: BindingContext) -> BindingFacts:
    facts = BindingFacts()
    for value in values:
        current = replace(context, local=context.local | facts.local)
        facts = merge_facts(facts, binding_facts(value, current))
    return facts


def declaration_facts(entries: list[Declarator], context: BindingContext) -> BindingFacts:
    facts = BindingFacts()
    for name, _, dimensions, initial in entries:
        current = replace(context, local=context.local | facts.local)
        facts = merge_facts(facts, sequence_facts(dimensions, current))
        shadowed = frozenset({name}) if name in context.enclosing else frozenset()
        facts = merge_facts(facts, BindingFacts(frozenset({name}), frozenset({name}), shadowed=shadowed))
        current = replace(context, local=context.local | facts.local)
        facts = merge_facts(facts, binding_facts(initial, current))
    return facts


def binding_facts(value: CValue, context: BindingContext) -> BindingFacts:
    if lexical_scope(value):
        nested = BindingContext(context.enclosing | context.local, frozenset())
        return replace(sequence_facts(syntax_children(value), nested), local=frozenset())
    match value:
        case ('decl', _, list() as entries):
            return declaration_facts(entries, context)
        case ('name', name):
            unresolved = frozenset() if name in context.enclosing | context.local else frozenset({name})
            return BindingFacts(unresolved=unresolved)
    return sequence_facts(syntax_children(value), context)


def shadowed_bindings(value: CValue, enclosing: frozenset[str]) -> frozenset[str]:
    facts = binding_facts(value, BindingContext(enclosing, frozenset()))
    return facts.shadowed | (facts.declared & facts.unresolved)
