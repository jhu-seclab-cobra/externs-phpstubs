"""Value operations of the handler extraction: constant folding, narrowing of unknown values by the tests of the path,
pointer arithmetic and C casts (design-extraction-handlers.md)."""

from handler_memory import (
    ANYV, Size, Alt, Fn, Masked, Ptr, Str, Sym, Test, Unknown, alternatives, known,
)

CAST_MASKS = {
    "uint8_t": 0xFF, "char": 0xFF, "zend_uchar": 0xFF, "uint16_t": 0xFFFF, "unsigned short": 0xFFFF,
    "uint32_t": 0xFFFFFFFF, "unsigned": 0xFFFFFFFF, "__int32": 0xFFFFFFFF, "uint64_t": 0xFFFFFFFFFFFFFFFF,
}
UNSIGNED_BITS = {"__int32": 0xFFFFFFFF, "uint32_t": 0xFFFFFFFF}


def arithmetic(operator, left, right):
    """The integer an operator gives on two integers, or None."""
    try:
        return {
            "+": lambda: left + right, "-": lambda: left - right, "*": lambda: left * right,
            "/": lambda: left // right if right else None, "%": lambda: left % right if right else None,
            "<<": lambda: left << right, ">>": lambda: left >> right, "&": lambda: left & right,
            "|": lambda: left | right, "^": lambda: left ^ right, "==": lambda: int(left == right),
            "!=": lambda: int(left != right), "<": lambda: int(left < right), ">": lambda: int(left > right),
            "<=": lambda: int(left <= right), ">=": lambda: int(left >= right),
            "&&": lambda: int(bool(left) and bool(right)), "||": lambda: int(bool(left) or bool(right)),
        }[operator]()
    except (KeyError, ValueError, OverflowError):
        return None


def facts_of(state, sid):
    return [(mask, fact) for (s, mask), fact in state.facts.items() if s == sid]


def resolve(value, state):
    """The constant a symbol or masked symbol equals on this path, else the value itself."""
    if isinstance(value, Sym):
        sym, mask = value, -1
    elif isinstance(value, Masked):
        sym, mask = value.sym, value.mask
    else:
        return value
    for known_mask, fact in facts_of(state, sym.sid):
        if fact[0] == "eq" and (known_mask == -1 or known_mask & mask == mask):
            return fact[1] & mask if mask != -1 else fact[1]
    return value


def as_test(value):
    """A symbol used as a condition tests its masked bits against zero."""
    if isinstance(value, Test):
        return value
    if isinstance(value, Sym):
        return Test(value, -1, False, 0)
    if isinstance(value, Masked):
        return Test(value.sym, value.mask, False, 0)
    return None


def decide(test, state):
    """True or False when the path settles the test, else None."""
    for mask, fact in facts_of(state, test.sym.sid):
        if fact[0] == "eq" and (mask == -1 or mask & test.mask == test.mask or mask == test.mask):
            same = (fact[1] & test.mask if test.mask != -1 else fact[1]) == test.const
            return same == test.equal
        if fact[0] == "ne" and mask == test.mask and test.const in fact[1]:
            return not test.equal
    return None


def truth(value, state):
    """True, False, or None for a value the path leaves open."""
    value = resolve(value, state)
    if isinstance(value, bool) or isinstance(value, int):
        return bool(value)
    if isinstance(value, (Ptr, Fn, Str)):
        return True
    test = as_test(value)
    return decide(test, state) if test is not None else None


def narrow(value, taken, state):
    """Record in the state what a taken or untaken test of the value establishes."""
    test = as_test(resolve(value, state))
    if test is None or decide(test, state) is not None:
        return
    equal = taken == test.equal
    key = (test.sym.sid, test.mask)
    if equal:
        state.facts[key] = ("eq", test.const)
        return
    old = state.facts.get(key)
    excluded = old[1] if old and old[0] == "ne" else frozenset()
    state.facts[key] = ("ne", frozenset(excluded | {test.const}))


def equality(operator, left, right, state):
    left, right = resolve(left, state), resolve(right, state)
    plain = (int, Ptr, Fn)
    if isinstance(left, plain) and isinstance(right, plain):
        same = left == right and not (isinstance(left, Ptr) and symbolic_region(left))
        distinct = left != right and not (symbolic_region(left) or symbolic_region(right))
        return int(same == (operator == "==")) if (same or distinct) else ANYV
    sym, other = (left, right) if isinstance(left, (Sym, Masked)) else (right, left)
    if isinstance(sym, (Sym, Masked)) and isinstance(other, int):
        mask = sym.mask if isinstance(sym, Masked) else -1
        base = sym.sym if isinstance(sym, Masked) else sym
        if mask != -1 and other & ~mask:
            return int(operator == "!=")
        return Test(base, mask, operator == "==", other)
    if isinstance(left, Sym) and left == right:
        return int(operator == "==")
    return ANYV


def symbolic_region(value):
    return isinstance(value, Ptr) and value.rid.startswith("y:")


def mask_bits(operator, left, right):
    if operator != "&":
        return ANYV
    sym, mask = (left, right) if isinstance(left, (Sym, Masked)) else (right, left)
    if not (isinstance(sym, (Sym, Masked)) and isinstance(mask, int)):
        return ANYV
    if isinstance(sym, Masked):
        return Masked(sym.sym, sym.mask & mask)
    return Masked(sym, mask)


def pointer_arithmetic(operator, left, right):
    if operator not in ("+", "-"):
        return ANYV
    pointer, offset = (left, right) if isinstance(left, Ptr) else (right, left)
    if isinstance(offset, Size):
        return Ptr(pointer.rid, pointer.path[:-1]) if operator == "-" and pointer.path else ANYV
    if not isinstance(offset, int):
        return ANYV
    step = offset if operator == "+" else -offset
    if step == 0:
        return pointer
    if pointer.path and isinstance(pointer.path[-1], int):
        return Ptr(pointer.rid, pointer.path[:-1] + (pointer.path[-1] + step,))
    return Ptr(pointer.rid, pointer.path + (step,))


def binary(operator, left, right, state):
    """The value of a binary operator on two plain values."""
    left, right = resolve(left, state), resolve(right, state)
    if isinstance(left, int) and isinstance(right, int):
        folded = arithmetic(operator, left, right)
        return ANYV if folded is None else folded
    if operator in ("==", "!="):
        return equality(operator, left, right, state)
    if isinstance(left, Ptr) or isinstance(right, Ptr):
        return pointer_arithmetic(operator, left, right)
    return mask_bits(operator, left, right)


def cast(words, value):
    """A C cast of a plain value: an integer type truncates, a pointer or other type keeps the value."""
    if "*" in words:
        return value
    typed = [w for w in words if w in CAST_MASKS]
    if not typed:
        return value
    mask = CAST_MASKS[typed[-1]]
    if isinstance(value, int):
        return value & mask
    if isinstance(value, Sym):
        return Masked(value, mask)
    if isinstance(value, Masked):
        return Masked(value.sym, value.mask & mask)
    return value if not isinstance(value, Unknown) else ANYV


def plain_values(value):
    """The (value, conditions) pairs of a possibly alternative value."""
    return alternatives(value) if isinstance(value, Alt) else ((value, ()),)


def bounded(value):
    return known(value) or isinstance(value, Sym)


def literals(condition):
    """The condition literals a source condition stands for: a conjunction splits, anything else stays whole."""
    return tuple(part.strip() for part in condition.split("&&") if part.strip())


def assume(value, constant, state):
    """Record that the value equals the constant on this path; False when the path already excludes it."""
    test = as_test(resolve(value, state))
    if test is None:
        return not isinstance(resolve(value, state), int) or resolve(value, state) == constant
    test = Test(test.sym, test.mask, True, constant)
    settled = decide(test, state)
    if settled is not None:
        return settled
    state.facts[(test.sym.sid, test.mask)] = ("eq", constant)
    return True


def exclude(value, constants, state):
    """Record that the value equals none of the constants; False when the path already pins it to one of them."""
    resolved = resolve(value, state)
    if isinstance(resolved, int):
        return resolved not in constants
    test = as_test(resolved)
    if test is None:
        return True
    if any(decide(Test(test.sym, test.mask, True, c), state) for c in constants):
        return False
    key = (test.sym.sid, test.mask)
    old = state.facts.get(key)
    state.facts[key] = ("ne", frozenset((old[1] if old and old[0] == "ne" else frozenset()) | set(constants)))
    return True
