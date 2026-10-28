"""Builtin variadic named-extra reception from the shared php-src C reader.

Only established parsing patterns produce a fact. Unknown source, alternative
handlers or reception operations leave the signature field unextracted.
"""

import re
from copy import copy

import compile_facts
from php_src_c.definitions import Call
from php_src_c.source import CALL, matching, split_arguments, statement_end

# Whitespace-collapsed bodies of the parsing primitives in the producer-pinned zend_API.h.
PRIMITIVES = {
    "ZEND_PARSE_PARAMETERS_START_EX": "ad781dafbfa5d5fc",
    "ZEND_PARSE_PARAMETERS_START": "3501601f6c0fe3e4",
    "ZEND_PARSE_PARAMETERS_END_EX": "1435e3461e39ef62",
    "ZEND_PARSE_PARAMETERS_END": "1c1507d3a4308932",
    "Z_PARAM_PROLOGUE": "b3be1a35c8caf187",
    "Z_PARAM_OPTIONAL": "cf4e4ffbb873a355",
    "Z_PARAM_VARIADIC_EX": "af75990214f50978",
    "Z_PARAM_VARIADIC": "9d856db06ed75dab",
    "Z_PARAM_VARIADIC_WITH_NAMED": "7cbecacb50f5dc5c",
}
PARSING = re.compile(
    r"\bZEND_PARSE_PARAMETERS_START\(\s*\d+\s*,\s*-1\s*\)(.*?)"
    r"\bZEND_PARSE_PARAMETERS_END\(\s*\)", re.S,
)
THIN_HELPER = re.compile(r"\{\s*(\w+)\(\s*INTERNAL_FUNCTION_PARAM_PASSTHRU\s*(.*?)\);\s*\}", re.S)
CONSTANT_IF = re.compile(r"\bif\s*\(\s*(\w+)\s*\)")
FORWARD = ("forward", None)
REJECTING = {"Z_PARAM_VARIADIC", "Z_PARAM_VARIADIC_EX"}
VARIADICS = REJECTING | {"Z_PARAM_VARIADIC_WITH_NAMED"}
KNOWN_CALLS = {"zend_call_known_function", "zend_call_known_fcc"}
CONTROL = re.compile(r"\b(?:if|else|for|while|switch|do|goto|return|RETURN_\w+)\b")
RECEPTION_WRITE = re.compile(r"(?:\+\+|--)\s*_i\b|\b_i\s*(?:\+\+|--|[+*/-]?=(?!=))")


def invocations(text):
    """Calls with their arguments, using the shared C reader's bracket handling."""
    for match in CALL.finditer(text):
        end = matching(text, match.end() - 1)
        if end >= 0:
            yield match, split_arguments(text[match.end():end]), end + 1


def primitives_match(program, source):
    for name, digest in PRIMITIVES.items():
        macro = program.preprocessor.lookup(source, name)
        if macro is None or compile_facts.digest(macro[1]) != digest:
            return False
    return True


def reception_count(program, source, name):
    """Count prologues through source macro aliases; unknown or recursive macros have no count."""
    def count(current, seen):
        if current == "Z_PARAM_PROLOGUE":
            return 1
        macro = program.preprocessor.lookup(source, current)
        if current in seen or macro is None or RECEPTION_WRITE.search(macro[1]):
            return None
        counts = [count(call.group(1), seen | {current}) for call in CALL.finditer(macro[1])
                  if program.preprocessor.lookup(source, call.group(1)) is not None]
        return None if None in counts else sum(counts)

    return count(name, frozenset())


def parsing_operations(text):
    """A plain sequence of parsing macro invocations, or None for an unread operation."""
    operations, at = [], 0
    while text[at:].strip(" \t\r\n;"):
        at += len(text[at:]) - len(text[at:].lstrip(" \t\r\n;"))
        call = CALL.match(text, at)
        if call is None:
            return None
        end = matching(text, call.end() - 1)
        if end < 0:
            return None
        operations.append((call.group(1), split_arguments(text[call.end():end])))
        at = end + 1
    return operations


def parsing_policy(program, definition, block):
    operations = parsing_operations(block.group(1))
    if operations is None or sum(name in VARIADICS for name, _ in operations) != 1:
        return None
    position = 0
    for name, args in operations:
        if name in REJECTING:
            prefix = definition.body[:block.start()]
            if CONTROL.search(prefix) or prefix.count("{") - prefix.count("}") != 1:
                return None
            return ("reject", position)
        if name == "Z_PARAM_VARIADIC_WITH_NAMED":
            return FORWARD if len(args) == 3 and forwards_named(program, definition, (args[2], block.end())) else None
        count = reception_count(program, definition.source, name)
        if count != 1:
            return None
        position += count
    return None


def calls_named(body, named):
    """The parsed collection is the explicit named-argument input of a callable invocation."""
    owner = named.removesuffix(".named_params")
    assigned = re.compile(r"(?<![\w.])(?:" + re.escape(named) + "|" + re.escape(owner) + r")\s*=(?!=)")
    for match, args, _ in invocations(body):
        if assigned.search(body[:match.start()]):
            return False
        if match.group(1) in KNOWN_CALLS and args and args[-1] == named:
            return True
        if named.endswith(".named_params") and match.group(1) == "zend_call_function":
            if args and args[0] == "&" + named.removesuffix(".named_params"):
                return True
    return False


def forwards_named(program, definition, parsed):
    named, after = parsed
    suffix = definition.body[after:]
    if calls_named(suffix, named):
        return True
    # A context entry receives the same stored fcall_info (Fiber's argument parsing).
    for _, args, _ in invocations(suffix):
        for arg in args:
            if not re.fullmatch(r"[A-Za-z_]\w*", arg):
                continue
            for target in program.resolve(definition, Call(arg, None, frozenset())):
                if calls_named(target.body, named):
                    return True
    return False


def select_constants(body, bindings):
    """Select only literal-bound helper branches; other conditions keep their source structure."""
    for match in list(CONSTANT_IF.finditer(body))[::-1]:
        if match.group(1) not in bindings:
            continue
        start = match.end()
        end = statement_end(body, start) + 1
        otherwise = re.match(r"\s*else\b", body[end:])
        final = statement_end(body, end + otherwise.end()) + 1 if otherwise else end
        selected = ""
        if bindings[match.group(1)]:
            selected = body[start:end]
        elif otherwise:
            selected = body[end + otherwise.end():final]
        body = body[:match.start()] + selected + body[final:]
    return body


def definition_policy(program, definition, seen=frozenset()):
    if id(definition) in seen or not primitives_match(program, definition.source):
        return None
    blocks = list(PARSING.finditer(definition.body))
    if len(re.findall(r"\bZEND_PARSE_PARAMETERS_START(?:_EX)?\s*\(", definition.body)) != len(blocks):
        return None
    if blocks:
        policies = [parsing_policy(program, definition, block) for block in blocks]
        return policies[0] if all(policy == policies[0] for policy in policies) else None
    helper = THIN_HELPER.fullmatch(definition.body)
    if helper is None:
        return None
    args = split_arguments(helper.group(2).lstrip().removeprefix(","))
    if any(arg not in ("0", "1") for arg in args):
        return None
    targets = program.resolve(definition, Call(helper.group(1), [], frozenset()))
    policies = [helper_policy(program, target, (args, seen | {id(definition)})) for target in targets]
    return policies[0] if policies and all(policy == policies[0] for policy in policies) else None


def helper_policy(program, target, context):
    args, seen = context
    if len(target.params) != len(args) + 1:
        return None
    # A local view preserves shared source definitions and linkage without changing Program.
    specialized = copy(target)
    specialized.body = select_constants(target.body, dict(zip(target.params[1:], map(int, args))))
    if id(target) in seen:
        return None
    return definition_policy(program, specialized, seen | {id(target)})


def read_policies(program, keys):
    """The policy of every requested builtin, requiring agreement across ordinary handlers and definitions."""
    entries, policies = program.entries(), {}
    for key in keys:
        handlers = [name for name in entries.get(key, ()) if not name.startswith("zflf_")]
        alternatives = [definition_policy(program, definition) for name in handlers
                        for definition in program.functions.get(name, ())]
        complete = handlers and all(program.functions.get(name) for name in handlers)
        policies[key] = alternatives[0] if complete and alternatives and all(p == alternatives[0] for p in alternatives) else None
    return policies
