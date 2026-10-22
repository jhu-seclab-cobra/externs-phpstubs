"""The facts php-src's call compiler fixes for a function call (design-extraction-signatures.md, extract_signatures.py).

Reads `Zend/zend_compile.c`: the by-name dispatch `zend_try_compile_special_func_ex` and the compile function each
dispatched name reaches. Every target has a recorded disposition, and the source of every function the facts rest on is
pinned by a digest, so a php-src change that alters the compiler fails the run instead of going unnoticed.
"""

import hashlib
import re

import php_src

COMPILER = "Zend/zend_compile.c"
STRINGS = "Zend/zend_string.h"
DISPATCH_FUNCTION = "zend_try_compile_special_func_ex"
# Calls with more arguments than this never select a frameless function (find_frameless_function_info).
MAX_FRAMELESS_ARGUMENTS = 3

# How a dispatch target compiles the arguments of its call to one opcode.
SPECIAL = "special counts: two or more arguments are operands of one opcode, so the count is a fact"
UNARY = "at most one operand: no operand order exists"
CONSTANT = "constant operands besides at most one: the other operands are read at compile time"
IN_PLACE = "arguments read where they stand: each argument evaluates in source order"
ROPE = "the rope: the constant format string fixes the order, and the format parameter is a fact"
MERGED = "the merged form of call_user_func_array with array_slice: a limit, no fact"

DISPOSITIONS = {
    "zend_compile_func_array_key_exists": SPECIAL,
    "zend_compile_func_strlen": UNARY,
    "zend_compile_func_typecheck": UNARY,
    "zend_compile_func_is_scalar": UNARY,
    "zend_compile_func_cast": UNARY,
    "zend_compile_func_chr": UNARY,
    "zend_compile_func_ord": UNARY,
    "zend_compile_func_count": UNARY,
    "zend_compile_func_get_class": UNARY,
    "zend_compile_func_get_called_class": UNARY,
    "zend_compile_func_gettype": UNARY,
    "zend_compile_func_num_args": UNARY,
    "zend_compile_func_get_args": UNARY,
    "zend_compile_func_clone": UNARY,
    "zend_compile_func_defined": CONSTANT,
    "zend_compile_func_in_array": CONSTANT,
    "zend_compile_func_cuf": IN_PLACE,
    "zend_compile_func_sprintf": ROPE,
    "zend_compile_func_cufa": MERGED,
    "zend_compile_func_array_slice": MERGED,
}
# Functions the facts rest on besides the dispatch targets.
PINNED = (
    "zend_try_compile_special_func",
    DISPATCH_FUNCTION,
    "find_frameless_function_info",
    "zend_compile_frameless_icall_ex",
    "zend_compile_ns_call",
    "zend_compile_func_cufa",
)
# Comment-stripped, whitespace-collapsed SHA-256 (first 16 hex digits) of each pinned function and target in php-8.5.11.
DIGESTS = {
    "find_frameless_function_info": "3d0fa3555667acbe",
    "zend_compile_frameless_icall_ex": "e2dd441645595655",
    "zend_compile_func_array_key_exists": "aaa29a6e9c6a0c3b",
    "zend_compile_func_array_slice": "631392bc78668092",
    "zend_compile_func_cast": "cbb794186d1b3555",
    "zend_compile_func_chr": "d8e3e4ab5bdb74e3",
    "zend_compile_func_clone": "5c0118e82ba6c78a",
    "zend_compile_func_count": "ef73b7ac2e1ee5f8",
    "zend_compile_func_cuf": "9eee9c42ce209061",
    "zend_compile_func_cufa": "ffcd8e99e4a6cf64",
    "zend_compile_func_defined": "68d932170cccb8c2",
    "zend_compile_func_get_args": "463a11bdc1772063",
    "zend_compile_func_get_called_class": "7150dd5a384c380f",
    "zend_compile_func_get_class": "0f151a20bead0a90",
    "zend_compile_func_gettype": "e96d45f215743644",
    "zend_compile_func_in_array": "4e28456254d45207",
    "zend_compile_func_is_scalar": "72f6550604816c7c",
    "zend_compile_func_num_args": "713946d739312095",
    "zend_compile_func_ord": "027906c76fdf46eb",
    "zend_compile_func_sprintf": "1f1ce24858cd5bea",
    "zend_compile_func_strlen": "fcaf8119c9da9f3f",
    "zend_compile_func_typecheck": "484d05e677059c3c",
    "zend_compile_ns_call": "f5d90a34562e1316",
    "zend_try_compile_special_func": "c28f2e58fa446098",
    "zend_try_compile_special_func_ex": "45b0a4fe113cdc41",
}

NAME_TEST = re.compile(r"\bzend_string_equals(?:_literal)?\(\s*lcname\s*,\s*(?:\"(\w+)\"|ZSTR_KNOWN\(\s*(\w+)\s*\))\s*\)")
LCNAME_TEST = re.compile(r"\bzend_string_equals\w*\(\s*lcname\b")
DISPATCH_TARGET = re.compile(r"\breturn\s+(zend_compile_func_\w+)\(")
KNOWN_STRING = re.compile(r'^\s*_\((\w+),\s*"(\w+)"\)', re.M)
OPERAND = re.compile(r"\bzend_compile_expr\(\s*&\w+\s*,\s*args->child\[(\d+)\]\s*\)")
ARGUMENT_COUNT_CHECK = re.compile(r"\bargs->children\s*!=\s*(\d+)")
FORMAT_OPERAND = re.compile(r"\bzend_eval_const_expr\(\s*&args->child\[(\d+)\]\s*\)")


class CompilerFacts:
    """Function name (lower case) → special argument count; function name → format parameter position."""

    def __init__(self, special, rope):
        self.special, self.rope = special, rope


def frameless_counts(tag_arities, required, variadic):
    """The argument counts 0..3 for which find_frameless_function_info picks an info: the first tag, in order, whose
    arity is at least the count, with the function requiring at most the count and, for a variadic function, an arity
    equal to the count."""
    counts = set()
    for count in range(MAX_FRAMELESS_ARGUMENTS + 1):
        if any(arity >= count and required <= count and (not variadic or arity == count) for arity in tag_arities):
            counts.add(count)
    return counts


def read_compiler(root, digests=None, pins=PINNED):
    """Check the closure over the dispatch and return its CompilerFacts; digests defaults to the pinned set and pins
    names the functions besides the dispatch targets that must match it."""
    digests = DIGESTS if digests is None else digests
    text = php_src.strip_comments((root / COMPILER).read_text(encoding="utf-8"), COMPILER)
    known = dict(KNOWN_STRING.findall((root / STRINGS).read_text(encoding="utf-8")))
    bodies = {name: function_text(text, name) for name in pins}
    dispatch = function_text(text, DISPATCH_FUNCTION)
    special, rope, targets, previous = {}, {}, set(), 0
    for target in DISPATCH_TARGET.finditer(dispatch):
        names = test_names(dispatch[previous : target.start()], known)
        previous = target.end()
        name = target.group(1)
        if name not in DISPOSITIONS:
            raise php_src.ExtractionFailure(f"{COMPILER}: {DISPATCH_FUNCTION} reaches {name}, which has no disposition")
        targets.add(name)
        body = bodies[name] = function_text(text, name)
        disposition = DISPOSITIONS[name]
        operands = set(OPERAND.findall(body))
        if disposition == SPECIAL:
            special.update(special_count(name, body, operands, names))
        elif disposition in (UNARY, CONSTANT) and len(operands) > 1:
            raise php_src.ExtractionFailure(f"{name}: operands {sorted(operands)} against the disposition {disposition!r}")
        elif disposition == ROPE:
            rope.update(rope_position(name, body, names))
    if not targets:
        raise php_src.ExtractionFailure(f"{COMPILER}: {DISPATCH_FUNCTION} dispatches to no compile function")
    check_digests(bodies, digests)
    return CompilerFacts(special, rope)


def test_names(segment, known):
    """The function names one dispatch branch tests, with every ZSTR_KNOWN symbol resolved."""
    names = []
    for literal, symbol in NAME_TEST.findall(segment):
        if symbol and symbol not in known:
            raise php_src.ExtractionFailure(f"{COMPILER}: ZSTR_KNOWN({symbol}) is not a name of {STRINGS}")
        names.append(literal or known[symbol])
    if not names or len(names) != len(LCNAME_TEST.findall(segment)):
        raise php_src.ExtractionFailure(f"{COMPILER}: a dispatch branch tests a name this reader does not resolve")
    return names


def special_count(name, body, operands, names):
    if len(operands) < 2:
        raise php_src.ExtractionFailure(f"{name}: the disposition {SPECIAL!r} needs two operands, found {sorted(operands)}")
    checks = set(ARGUMENT_COUNT_CHECK.findall(body))
    if checks != {str(len(operands))}:
        raise php_src.ExtractionFailure(f"{name}: operands {sorted(operands)} against argument count checks {sorted(checks)}")
    return {n: len(operands) for n in names}


def rope_position(name, body, names):
    positions = set(FORMAT_OPERAND.findall(body))
    if len(positions) != 1:
        raise php_src.ExtractionFailure(f"{name}: no single format operand, found {sorted(positions)}")
    return {n: int(next(iter(positions))) for n in names}


def function_text(text, name):
    """The definition of the C function name: its head and body."""
    head = re.search(rf"^[A-Za-z_][\w \t\*]*\b{name}\([^)]*\)\s*\{{", text, re.M)
    if head is None:
        raise php_src.ExtractionFailure(f"{COMPILER}: no definition of {name}")
    return text[head.start() : php_src.matching(text, head.end() - 1, COMPILER) + 1]


def digest(text):
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()[:16]


def check_digests(bodies, digests):
    changed = sorted(name for name, body in bodies.items() if digests.get(name) != digest(body))
    if changed:
        raise php_src.ExtractionFailure(f"{COMPILER}: changed or unpinned compiler functions {changed}")
