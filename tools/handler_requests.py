"""The requests the engine makes of object handlers (spec-extraction-handlers.md step 7): the type tags passed to
``cast_object`` and the opcodes passed to ``do_operation``, read from the call sites of one php-src checkout."""

import re

from php_src_c.source import IDENTIFIER, matching, split_arguments

SLOTS = re.compile(r"\b(cast_object|do_operation)\b")
CALL = re.compile(r"->\s*(cast_object|do_operation)\s*\)*\s*\(")
INTEGER = re.compile(r"^\(?\s*-?(0x[0-9a-fA-F]+|\d+)\s*\)?$")
TAG = re.compile(r"^_?IS_[A-Z_]+$")
OPCODE = re.compile(r"^ZEND_[A-Z_]+$")
COMPARE_CALL = re.compile(r"->\s*compare\s*\)*\s*\(|Z_OBJ_HANDLER(?:_P)?\([^()]*,\s*compare\s*\)\s*\(")
FIRST_TAG, LAST_TAG = "IS_NULL", "IS_RESOURCE"


def forwarding_macros(preprocessor):
    """The function-like macros that mention a handler slot, directly or through another such macro."""
    bodies = {}
    for table in list(preprocessor.locals.values()) + [preprocessor.headers]:
        for name, (params, body) in table.items():
            if params is not None:
                bodies.setdefault(name, []).append(body)
    found = {name for name, texts in bodies.items() if any(SLOTS.search(t) for t in texts)}
    grown = True
    while grown:
        grown = False
        for name, texts in bodies.items():
            if name not in found and any(set(IDENTIFIER.findall(t)) & found for t in texts):
                found.add(name)
                grown = True
    return found


def constant_macros(preprocessor):
    """The object-like macros that stand for an integer: they name a tag or an opcode and are not expanded."""
    names = set()
    for table in list(preprocessor.locals.values()) + [preprocessor.headers]:
        names.update(n for n, (params, body) in table.items() if params is None and INTEGER.match(body.strip()))
    return frozenset(names)


def tag_values(preprocessor):
    """The tag names IS_NULL..IS_RESOURCE of the header that defines the value tags, with their numeric values."""
    for table in preprocessor.locals.values():
        if FIRST_TAG in table and LAST_TAG in table:
            return {name: int(body.strip().strip("()").strip(), 0) for name, (params, body) in table.items()
                    if params is None and TAG.match(name) and INTEGER.match(body.strip())}
    return {}


def request_arguments(text):
    """The (slot, request expression) pairs of the handler calls in an expanded function body."""
    pairs = []
    for match in CALL.finditer(text):
        opening = match.end() - 1
        arguments = split_arguments(text[opening + 1:matching(text, opening, "(", ")")])
        index = 2 if match.group(1) == "cast_object" else 0
        pairs.append((match.group(1), " ".join(arguments[index].split())))
    return pairs


def guarded_tags(body, variable):
    """The tags a function asserts a variable, or the type of the value it came from, is not."""
    return set(re.findall(r"\b(?:%s|Z_TYPE_P\(\w+\))\s*!=\s*(_?IS_[A-Z_]+)" % re.escape(variable), body))


def comparing_functions(program):
    """The functions that call an object handler's ``compare`` and the functions that call those."""
    direct = {d.name for ds in program.functions.values() for d in ds
              if not d.is_macro and COMPARE_CALL.search(d.body)}
    callers = {d.name for ds in program.functions.values() for d in ds
               if not d.is_macro and direct & set(re.findall(r"\b(\w+)\s*\(", d.body))}
    return direct | callers


def object_pair_tags(program):
    """The tags T of every ``TYPE_PAIR(IS_OBJECT, T)`` and ``TYPE_PAIR(T, IS_OBJECT)`` case in the functions that
    reach an object handler's ``compare``: they settle those pairs before they call the handler."""
    tags, names = set(), comparing_functions(program)
    for name in names:
        for definition in program.functions.get(name, ()):
            tags.update(re.findall(r"TYPE_PAIR\(IS_OBJECT,\s*(_?IS_\w+)\)", definition.body))
            tags.update(re.findall(r"TYPE_PAIR\((_?IS_\w+),\s*IS_OBJECT\)", definition.body))
    return tags


def flowing_tags(program, body, variable):
    """The tags a variable that holds the type of an operand can take: every tag from IS_NULL to IS_RESOURCE that
    the function and the comparison dispatcher do not exclude. Empty when the variable does not hold a type."""
    if not re.search(r"\b%s\s*=\s*Z_TYPE_P?\(" % re.escape(variable), body):
        return set()
    values = tag_values(program.preprocessor)
    first, last = values[FIRST_TAG], values[LAST_TAG]
    universe = {name for name, value in values.items() if first <= value <= last}
    handled = guarded_tags(body, variable) | object_pair_tags(program) | {"IS_OBJECT"}
    return universe - handled


def consumed_requests(program):
    """The (cast tags, operation opcodes) the engine passes to the handlers, as sets of names."""
    preprocessor = program.preprocessor
    forwarding, protected = forwarding_macros(preprocessor), constant_macros(preprocessor)
    casts, operations = set(), set()
    for definitions in program.functions.values():
        for definition in definitions:
            if definition.is_macro or not mentions_slot(definition.body, forwarding):
                continue
            text = preprocessor.expand(definition.body, definition.source, protected)
            for slot, request in request_arguments(text):
                names = request_names(program, definition, request)
                (casts if slot == "cast_object" else operations).update(names)
    return casts, operations


def mentions_slot(body, forwarding):
    return bool(SLOTS.search(body)) or bool(set(IDENTIFIER.findall(body)) & forwarding)


def request_names(program, definition, request):
    """The tag or opcode names one request expression stands for."""
    if TAG.match(request) or OPCODE.match(request):
        return {request}
    return flowing_tags(program, definition.body, request)
