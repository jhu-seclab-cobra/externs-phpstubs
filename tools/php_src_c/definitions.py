"""C function definitions of a php-src checkout: heads, bodies, call sites and the call graph's components
(design-extraction-handlers.md)."""

import collections
import re

import php_src
from php_src_c.macros import HANDLER_MACROS
from php_src_c.source import CALL, matching, matching_brace, parameter_name, split_arguments, statement_end, strip_parentheses

ASSIGNMENT = re.compile(r"\b([A-Za-z_]\w*)\s*=(?!=)")
RETURN = re.compile(r"\breturn\b")
IF = re.compile(r"\bif\s*\(")
ELSE = re.compile(r"\s*else\b")
LINKAGE_BLOCK = re.compile(r"\bextern\s+__STR_\d+__\s*$")
NOT_CALLS = {
    "if", "while", "for", "switch", "return", "sizeof", "do", "else", "case", "defined", "__attribute__",
    "typeof", "_Alignof", "offsetof", "__typeof__", "__builtin_expect", "EXPECTED", "UNEXPECTED",
}
# A local declaration at the start of a statement: a type name, pointer marks, and the declared name.
LOCAL_DECLARATION = re.compile(r"(?:^|[{;}])\s*(?:(?:const|static|struct|unsigned|signed|volatile)\s+)*[A-Za-z_]\w*\s*[\s*]\s*\**\s*([A-Za-z_]\w*)\s*(?=[;,=\[])")
REFERENCE = re.compile(r"(?<![=!]=)(?<![=!]=\s)\b([A-Za-z_]\w*)\b(?!\s*(?:\(|[=!]=))")


class Definition:
    """One C function or function-like macro: its file, parameters, body, and whether it returns a class entry."""

    def __init__(self, name, source, params, body, returns_class, is_static, is_macro=False):
        self.name, self.source, self.params, self.body = name, source, params, body
        self.returns_class, self.is_static, self.is_macro = returns_class, is_static, is_macro
        self.calls, self.assignments, self.returns = [], collections.defaultdict(list), []

    def index(self, name):
        return self.params.index(name) if name in self.params else None


def definitions_of(source):
    """Yield every top-level function definition of a file; a brace no brace closes fails the run."""
    text, depth_start, i = source.text, 0, 0
    while True:
        brace = text.find("{", i)
        if brace < 0:
            return
        end = matching_brace(text, brace)
        if end < 0:
            raise php_src.ExtractionFailure(f"{source.relative}: unbalanced brace at offset {brace}")
        head = text[depth_start:brace]
        if LINKAGE_BLOCK.search(head):
            i = depth_start = brace + 1
            continue
        definition = definition_head(head, source, text[brace:end + 1])
        if definition:
            yield definition
        i = depth_start = end + 1


def definition_head(head, source, body):
    stripped = head.rstrip()
    if not stripped.endswith(")"):
        return None
    close = len(stripped) - 1
    depth, open_ = 0, None
    for j in range(close, -1, -1):
        depth += (stripped[j] == ")") - (stripped[j] == "(")
        if depth == 0:
            open_ = j
            break
    if open_ is None:
        return None
    name_match = re.search(r"([A-Za-z_]\w*)\s*$", stripped[:open_])
    if not name_match or name_match.group(1) in NOT_CALLS:
        return None
    name, arguments = name_match.group(1), split_arguments(stripped[open_ + 1:close])
    prefix = stripped[:name_match.start()]
    prefix = prefix[max(prefix.rfind(";"), prefix.rfind("}")) + 1:]
    if name in HANDLER_MACROS:
        return Definition(HANDLER_MACROS[name].format(*arguments), source, [], body, False, False)
    params = [p for p in (parameter_name(a) for a in arguments) if p]
    return Definition(name, source, params, body, "zend_class_entry" in prefix, "static" in prefix)


# The argument expression of a function reference, whose call site is not in the body; it resolves to no class.
UNKNOWN_ARGUMENT = "__ARGUMENT__"


class Call:
    """One call in a body: callee name, argument expressions, and the parameter guards at its position. A function
    named as a value is a call whose arguments are unknown (args None): the body may pass it on to be called."""

    def __init__(self, name, args, guards):
        self.name, self.args, self.guards = name, args, guards

    def argument(self, index, absent):
        """The expression of one argument; absent when the call passes fewer, unknown for a function reference."""
        if self.args is None:
            return UNKNOWN_ARGUMENT
        return self.args[index] if index < len(self.args) else absent



def split_conjuncts(condition):
    parts, depth, start, j = [], 0, 0, 0
    while j < len(condition):
        ch = condition[j]
        depth += (ch == "(") - (ch == ")")
        if depth == 0 and condition.startswith("&&", j):
            parts.append(condition[start:j])
            start = j = j + 2
            continue
        j += 1
    parts.append(condition[start:])
    return [strip_parentheses(p) for p in parts]


def parameter_guard(conjunct, params):
    """(parameter index, required truth) when the conjunct tests one parameter, else None."""
    negated = conjunct.startswith("!")
    name = strip_parentheses(conjunct[1:]) if negated else conjunct
    return (params.index(name), not negated) if name in params else None


def guard_ranges(body, params):
    """(start, end, guards) of every branch an if statement guards by parameters."""
    ranges = []
    for match in IF.finditer(body):
        close = matching(body, match.end() - 1)
        if close < 0:
            continue
        conjuncts = split_conjuncts(body[match.end():close])
        guards = [g for g in (parameter_guard(c, params) for c in conjuncts) if g]
        if not guards:
            continue
        then_end = statement_end(body, close + 1)
        ranges.append((close + 1, then_end, frozenset(guards)))
        otherwise = ELSE.match(body, then_end + 1)
        if otherwise and len(conjuncts) == 1:
            index, truth = guards[0]
            ranges.append((otherwise.end(), statement_end(body, otherwise.end()), frozenset({(index, not truth)})))
    return ranges


def consistent(guards):
    return len({index for index, _ in guards}) == len(guards)


def analyze(definition, functions):
    """Record the calls, function references, local assignments, and returned expressions of one body."""
    body, params = definition.body, definition.params
    ranges = guard_ranges(body, params) if params else []
    for match in CALL.finditer(body):
        name = match.group(1)
        if name in NOT_CALLS or member_access(body, match.start()):
            continue
        close = matching(body, match.end() - 1)
        if close >= 0:
            record(definition, Call(name, split_arguments(body[match.end():close]), position_guards(ranges, match.start())))
    shadowing = set(params) | set(LOCAL_DECLARATION.findall(body))
    for match in REFERENCE.finditer(body):
        name = match.group(1)
        if name in functions and name not in shadowing and not member_access(body, match.start()):
            record(definition, Call(name, None, position_guards(ranges, match.start())))
    for match in ASSIGNMENT.finditer(body):
        if member_access(body, match.start()):
            continue
        definition.assignments[match.group(1)].append(body[match.end():statement_end(body, match.end())].rstrip(";"))
    for match in RETURN.finditer(body):
        definition.returns.append(body[match.end():statement_end(body, match.end())].rstrip(";"))


def member_access(body, offset):
    return body[max(0, offset - 4):offset].rstrip().endswith(("->", "."))


def position_guards(ranges, offset):
    return frozenset(g for start, end, guards in ranges if start <= offset <= end for g in guards)


def record(definition, call):
    if consistent(call.guards):
        definition.calls.append(call)


def strongly_connected(nodes, edges):
    """Tarjan's components, callees before callers."""
    index, low, on_stack, stack, order, counter = {}, {}, set(), [], [], [0]
    for root in nodes:
        if root in index:
            continue
        work = [(root, iter(edges[root]))]
        index[root] = low[root] = counter[0]
        counter[0] += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, successors = work[-1]
            advanced = False
            for successor in successors:
                if successor not in index:
                    index[successor] = low[successor] = counter[0]
                    counter[0] += 1
                    stack.append(successor)
                    on_stack.add(successor)
                    work.append((successor, iter(edges[successor])))
                    advanced = True
                    break
                if successor in on_stack:
                    low[node] = min(low[node], index[successor])
            if advanced:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
            if low[node] == index[node]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                order.append(component)
    return order
