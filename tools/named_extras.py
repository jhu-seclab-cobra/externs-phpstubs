"""Builtin variadic named-extra reception from the shared php-src C reader.

Only established parsing patterns produce a fact. Unknown source, alternative
handlers or reception operations leave the signature field unextracted.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, TypeAlias

import compile_facts
from php_src_c import Program, Source
from named_extras_flow import Forwarding, ParsedCollection
from named_extras_reception import Operation, reception_count
from php_src_c.definitions import Call, Definition
from php_src_c.source import CALL, matching, split_arguments

Policy: TypeAlias = tuple[Literal["reject"], int] | tuple[Literal["forward"], None] | None
Subject: TypeAlias = tuple[str, str]
HelperContext: TypeAlias = tuple[list[str], frozenset[int]]

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
FORWARD = ("forward", None)
REJECTING = {"Z_PARAM_VARIADIC", "Z_PARAM_VARIADIC_EX"}
VARIADICS = REJECTING | {"Z_PARAM_VARIADIC_WITH_NAMED"}
CONTROL = re.compile(r"\b(?:if|else|for|while|switch|do|goto|return|RETURN_\w+)\b")


@dataclass(frozen=True)
class Binding:
    values: tuple[int, ...] = ()
    seen: frozenset[int] = frozenset()


@dataclass(frozen=True)
class ParsingGroup:
    block: re.Match[str]
    binding: Binding


def primitives_match(program: Program, source: Source) -> bool:
    for name, digest in PRIMITIVES.items():
        macro = program.preprocessor.lookup(source, name)
        if macro is None or compile_facts.digest(macro[1]) != digest:
            return False
    return True


def parsing_operations(text: str) -> list[Operation] | None:
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


def parsing_policy(flow: Forwarding, definition: Definition, group: ParsingGroup) -> Policy:
    operations = parsing_operations(group.block.group(1))
    if operations is None or sum(name in VARIADICS for name, _ in operations) != 1:
        return None
    position = 0
    for index, (name, args) in enumerate(operations):
        if name in REJECTING:
            return rejecting_policy(definition, group.block, position)
        if name == "Z_PARAM_VARIADIC_WITH_NAMED":
            if len(args) != 3:
                return None
            inputs = tuple(values[0] for operation, values in operations[:index] if values)
            parsed = ParsedCollection(group.block.start(), group.block.end(), args[2], inputs, group.binding.values)
            return FORWARD if flow.proves(definition, parsed) else None
        count = reception_count(flow.program, definition.source, (name, args))
        if count is None:
            return None
        position += count
    return None


def rejecting_policy(definition: Definition, block: re.Match[str], position: int) -> Policy:
    prefix = definition.body[:block.start()]
    if CONTROL.search(prefix) or prefix.count("{") - prefix.count("}") != 1:
        return None
    return ("reject", position)


def definition_policy(flow: Forwarding, definition: Definition, binding: Binding = Binding()) -> Policy:
    if id(definition) in binding.seen or not primitives_match(flow.program, definition.source):
        return None
    blocks = list(PARSING.finditer(definition.body))
    if len(re.findall(r"\bZEND_PARSE_PARAMETERS_START(?:_EX)?\s*\(", definition.body)) != len(blocks):
        return None
    if blocks:
        policies = [parsing_policy(flow, definition, ParsingGroup(block, binding)) for block in blocks]
        return policies[0] if all(policy == policies[0] for policy in policies) else None
    helper = THIN_HELPER.fullmatch(definition.body)
    if helper is None:
        return None
    args = split_arguments(helper.group(2).lstrip().removeprefix(","))
    if any(arg not in ("0", "1") for arg in args):
        return None
    targets = flow.program.resolve(definition, Call(helper.group(1), [], frozenset()))
    policies = [helper_policy(flow, target, (args, binding.seen | {id(definition)})) for target in targets]
    return policies[0] if policies and all(policy == policies[0] for policy in policies) else None


def helper_policy(flow: Forwarding, target: Definition, context: HelperContext) -> Policy:
    args, seen = context
    if len(target.params) != len(args) + 1:
        return None
    return definition_policy(flow, target, Binding((0, *map(int, args)), seen))


def read_policies(program: Program, keys: Iterable[Subject]) -> dict[Subject, Policy]:
    """The policy of every requested builtin, requiring agreement across ordinary handlers and definitions."""
    entries, policies = program.entries(), {}
    flow = Forwarding(program)
    for key in keys:
        handlers = [name for name in entries.get(key, ()) if not name.startswith("zflf_")]
        alternatives = [definition_policy(flow, definition) for name in handlers
                        for definition in program.functions.get(name, ())]
        complete = handlers and all(program.functions.get(name) for name in handlers)
        policies[key] = alternatives[0] if complete and alternatives and all(p == alternatives[0] for p in alternatives) else None
    return policies
