"""Admission of lexical bindings before the shared C compiler flattens blocks."""

from named_extras_reception import CNode, CValue


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


def scope_nodes(value: CValue) -> list[CNode]:
    if lexical_scope(value):
        return []
    own = [value] if isinstance(value, tuple) and value else []
    return own + [node for child in syntax_children(value) for node in scope_nodes(child)]


def shadowed_bindings(value: CValue, enclosing: frozenset[str]) -> frozenset[str]:
    if not isinstance(value, (tuple, list)) or not value:
        return frozenset()
    shadowed: frozenset[str] = frozenset()
    if lexical_scope(value):
        nodes = scope_nodes(value[1:])
        local = frozenset(entry[0] for node in nodes if node[0] == 'decl' for entry in node[2])
        references = frozenset(node[1] for node in nodes if node[0] == 'name')
        shadowed = local & enclosing
        enclosing = enclosing | local | references
    return shadowed.union(*(shadowed_bindings(child, enclosing) for child in syntax_children(value)))
