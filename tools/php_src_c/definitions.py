"""C function definitions of a php-src checkout: heads, bodies, call sites and the call graph's components
(design-extraction-handlers.md)."""

import collections
import re

import php_src
from php_src_c.macros import HANDLER_MACROS
from php_src_c.source import (
    BRANCH, CALL, STRING_PLACEHOLDER, matching, matching_brace, parameter_name, split_arguments, statement_end,
    strip_parentheses,
)

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


# ---------------------------------------------------------------------------------------------------------------------
# The statement and expression parser of a function body (design-extraction-handlers.md): the C subset php-src writes
# after macro expansion, parsed into tuples an abstract interpreter walks. A statement the parser cannot read becomes
# an ("opaque", text) statement; the caller decides whether that is admissible.

TOKEN = re.compile(
    r"\s+|(?P<num>0[xX][0-9a-fA-F]+[uUlL]*|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?[uUlLfF]*)|(?P<id>[A-Za-z_]\w*)"
    r"|(?P<op>\.\.\.|<<=|>>=|->|\+\+|--|<<|>>|<=|>=|==|!=|&&|\|\||[-+*/%&|^]=|.)", re.S)
ATTRIBUTE = re.compile(r"\b__attribute__\s*\(\s*\(")
TYPE_KEYWORDS = {
    "const", "static", "struct", "union", "enum", "unsigned", "signed", "volatile", "register", "extern", "inline",
    "int", "char", "long", "short", "double", "float", "void", "bool", "_Bool", "size_t", "ssize_t", "typeof",
    "__typeof__", "restrict", "__restrict", "zend_always_inline", "zend_never_inline", "ZEND_API",
}
STATEMENT_KEYWORDS = {"if", "else", "while", "do", "for", "switch", "case", "default", "break", "continue", "return", "goto"}
BINARY = {
    "||": 4, "&&": 5, "|": 6, "^": 7, "&": 8, "==": 9, "!=": 9, "<": 10, ">": 10, "<=": 10, ">=": 10, "<<": 11,
    ">>": 11, "+": 12, "-": 12, "*": 13, "/": 13, "%": 13,
}
ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}


class ParseFailure(Exception):
    """A body the parser cannot read."""


def tokens_of(text):
    """The (kind, text) tokens of a body; kind is num, id, str, or op."""
    text = strip_attributes(text)
    out = []
    for match in TOKEN.finditer(text):
        if match.lastgroup is None:
            continue
        kind, value = match.lastgroup, match.group()
        if kind == "id" and STRING_TOKEN.fullmatch(value):
            kind = "str"
        out.append((kind, value))
    return out


STRING_TOKEN = re.compile(r"__STR_\d+__")


def strip_attributes(text):
    while True:
        match = ATTRIBUTE.search(text)
        if not match:
            return text
        close = matching(text, match.end() - 2, "(", ")")
        if close < 0:
            return text
        text = text[:match.start()] + " " + text[close + 1:]


def parse_number(text):
    digits = text.rstrip("uUlL") if text[:2].lower() == "0x" else text.rstrip("uUlLfF")
    try:
        return int(digits, 16) if digits[:2].lower() == "0x" else int(digits, 8) if re.fullmatch(r"0\d+", digits) else int(digits)
    except ValueError:
        return None


class BodyParser:
    """Recursive-descent parser of one C body. ``variables`` are the names declared so far, which tells a cast from a
    parenthesized name."""

    def __init__(self, text, variables=()):
        self.toks, self.i, self.variables = tokens_of(text), 0, set(variables)

    # -- token access --
    def peek(self, k=0):
        return self.toks[self.i + k][1] if self.i + k < len(self.toks) else ""

    def kind(self, k=0):
        return self.toks[self.i + k][0] if self.i + k < len(self.toks) else "eof"

    def take(self):
        token = self.toks[self.i]
        self.i += 1
        return token[1]

    def expect(self, text):
        if self.peek() != text:
            raise ParseFailure(f"expected {text!r}, found {self.peek()!r} at token {self.i}")
        self.i += 1

    def accept(self, text):
        if self.peek() == text and self.kind() != "str":
            self.i += 1
            return True
        return False

    # -- statements --
    def body(self):
        """The statements of a braced body."""
        self.expect("{")
        block = self.block_rest()
        if self.i != len(self.toks):
            raise ParseFailure("text after the body")
        return block

    def block_rest(self):
        statements = []
        while self.peek() != "}":
            if self.kind() == "eof":
                raise ParseFailure("unterminated block")
            statements.append(self.statement())
        self.i += 1
        return ("block", statements)

    def statement(self):
        start = self.i
        try:
            return self.statement_unchecked()
        except ParseFailure:
            self.i = start
            return self.opaque()

    def opaque(self):
        """Skip a statement: to the next top-level ';', or past a braced block."""
        depth, start = 0, self.i
        while self.i < len(self.toks):
            token = self.peek()
            self.i += 1
            if token in ("(", "["):
                depth += 1
            elif token in (")", "]"):
                depth -= 1
            elif token == "{":
                if depth == 0:
                    depth = -1
                    break
                depth += 1
            elif token == "}":
                depth -= 1
            elif token == ";" and depth == 0:
                return ("opaque", " ".join(t for _, t in self.toks[start:self.i]))
        if depth == -1:
            nested = 1
            while self.i < len(self.toks) and nested:
                token = self.take()
                nested += (token == "{") - (token == "}")
            return ("opaque", " ".join(t for _, t in self.toks[start:self.i]))
        raise ParseFailure("unterminated statement")

    def statement_unchecked(self):
        token = self.peek()
        if self.kind() == "op" and token == "{":
            self.i += 1
            return self.block_rest()
        if self.kind() == "op" and token == ";":
            self.i += 1
            return ("empty",)
        if self.kind() == "id" and BRANCH.fullmatch(token):
            return self.group()
        if self.kind() == "id":
            handler = getattr(self, f"stmt_{token}", None)
            if handler and token in STATEMENT_KEYWORDS:
                self.i += 1
                return handler()
            if self.peek(1) == ":" and self.kind(1) == "op" and token not in TYPE_KEYWORDS:
                self.i += 2
                return ("label", token)
        declaration = self.try_declaration()
        if declaration:
            return declaration
        expression = self.expression()
        if self.peek() == ";":
            self.i += 1
        elif self.peek() not in ("{", "}"):
            raise ParseFailure(f"expected ';', found {self.peek()!r}")
        return ("expr", expression)

    def mark(self, k=0):
        """The (group, branch) of the conditional-compilation marker at the next token, or None."""
        found = BRANCH.fullmatch(self.peek(k)) if self.kind(k) == "id" else None
        return (int(found.group(1)), found.group(2)) if found else None

    def group(self):
        """A conditional-compilation group of statements: ("cgroup", group, [(branch, statements)])."""
        start, (group, _) = self.i, self.mark()
        try:
            return self.group_branches(group)
        except ParseFailure:
            end = f"__BRANCH_{group}_END__"
            at = next((j for j in range(start, len(self.toks)) if self.toks[j][1] == end), None)
            if at is None:
                raise
            self.i = at + 1
            return ("opaque", f"conditional group {group}")

    def group_branches(self, group):
        branches = []
        while True:
            marker = self.mark()
            if marker is None or marker[0] != group:
                raise ParseFailure("conditional group is not closed")
            self.i += 1
            if marker[1] == "END":
                return ("cgroup", group, branches)
            statements = []
            while self.mark() is None or self.mark()[0] != group:
                if self.kind() == "eof" or self.peek() == "}":
                    raise ParseFailure("conditional branch is not closed")
                statements.append(self.statement())
            branches.append((int(marker[1]), statements))

    def stmt_if(self):
        self.expect("(")
        condition = self.expression()
        self.expect(")")
        then = self.statement()
        otherwise = self.statement() if self.accept("else") else None
        return ("if", condition, then, otherwise)

    def stmt_while(self):
        self.expect("(")
        condition = self.expression()
        self.expect(")")
        return ("while", condition, self.statement())

    def stmt_do(self):
        body = self.statement()
        self.expect("while")
        self.expect("(")
        condition = self.expression()
        self.expect(")")
        self.accept(";")
        return ("do", body, condition)

    def stmt_for(self):
        self.expect("(")
        if self.accept(";"):
            init = ("empty",)
        else:
            init = self.try_declaration() or ("expr", self.expression_then(";"))
        condition = None if self.peek() == ";" else self.expression()
        self.expect(";")
        step = None if self.peek() == ")" else self.expression()
        self.expect(")")
        return ("for", init, condition, step, self.statement())

    def expression_then(self, closer):
        expression = self.expression()
        self.expect(closer)
        return expression

    def stmt_switch(self):
        self.expect("(")
        subject = self.expression()
        self.expect(")")
        return ("switch", subject, self.statement())

    def stmt_case(self):
        value = self.ternary()
        if self.accept("..."):
            raise ParseFailure("case range")
        self.expect(":")
        return ("case", value)

    def stmt_default(self):
        self.expect(":")
        return ("default",)

    def stmt_break(self):
        self.expect(";")
        return ("break",)

    def stmt_continue(self):
        self.expect(";")
        return ("continue",)

    def stmt_return(self):
        value = None if self.peek() == ";" else self.expression()
        self.expect(";")
        return ("return", value)

    def stmt_goto(self):
        label = self.take()
        self.expect(";")
        return ("goto", label)

    # -- declarations --
    def try_declaration(self):
        """A declaration statement: type words and stars, then declarators. None when the tokens are an expression."""
        j, words, stars = self.i, [], 0
        while j < len(self.toks) and self.toks[j][0] == "id" and self.toks[j][1] not in STATEMENT_KEYWORDS:
            words.append(self.toks[j][1])
            j += 1
            if words[-1] in ("struct", "union", "enum") and j < len(self.toks) and self.toks[j][0] == "id":
                words.append(self.toks[j][1])
                j += 1
        while j < len(self.toks) and self.toks[j] == ("op", "*"):
            stars += 1
            j += 1
            while j < len(self.toks) and self.toks[j][1] in ("const", "volatile", "restrict", "__restrict"):
                j += 1
        if stars:
            name_at, type_words = j, words
            need = 1
        else:
            name_at, type_words = j - 1, words[:-1]
            need = 2
        if len(words) < need or name_at >= len(self.toks) or self.toks[name_at][0] != "id":
            return None
        if self.toks[name_at][1] in STATEMENT_KEYWORDS or "sizeof" in words:
            return None
        follower = self.toks[name_at + 1][1] if name_at + 1 < len(self.toks) else ""
        if follower not in ("=", ";", ",", "["):
            return None
        if len(words) == 1 and words[0] in self.variables:
            return None
        self.i = name_at - (0 if stars else 0)
        declarators, pointer = [], stars
        while True:
            if self.kind() != "id":
                raise ParseFailure("declarator name")
            name = self.take()
            dims = []
            while self.accept("["):
                dims.append(None if self.peek() == "]" else self.expression())
                self.expect("]")
            init = self.initializer() if self.accept("=") else None
            self.variables.add(name)
            declarators.append((name, pointer, dims, init))
            if not self.accept(","):
                break
            pointer = 0
            while self.accept("*"):
                pointer += 1
        if not self.accept(";"):
            raise ParseFailure(f"expected ';' after a declaration, found {self.peek()!r}")
        return ("decl", tuple(type_words), declarators)

    def initializer(self):
        if self.peek() != "{" or self.kind() != "op":
            return self.assignment()
        self.i += 1
        items, active = [], []
        while self.peek() != "}":
            if self.mark():
                self.initializer_mark(active)
                continue
            designators = []
            while self.peek() in (".", "[") and self.kind() == "op":
                if self.accept("."):
                    designators.append(self.take())
                else:
                    self.i += 1
                    designators.append(("index", self.expression()))
                    self.expect("]")
            if designators:
                self.expect("=")
            items.append((tuple(designators), self.initializer(), tuple(active)))
            if not self.accept(","):
                break
        while self.mark():
            self.initializer_mark(active)
        self.expect("}")
        return ("init", items)

    def initializer_mark(self, active):
        """Track the conditional branches an initializer item stands under: (group, branch) pairs."""
        group, branch = self.mark()
        self.i += 1
        if branch == "END":
            active[:] = [a for a in active if a[0] != group]
        elif any(a[0] == group for a in active):
            active[:] = [(g, int(branch)) if g == group else (g, b) for g, b in active]
        else:
            active.append((group, int(branch)))

    # -- expressions --
    def expression(self):
        left = self.assignment()
        while self.peek() == "," and self.kind() == "op":
            self.i += 1
            left = ("comma", left, self.assignment())
        return left

    def assignment(self):
        left = self.ternary()
        if self.kind() == "op" and self.peek() in ASSIGN_OPS:
            operator = self.take()
            return ("assign", operator, left, self.assignment())
        return left

    def ternary(self):
        condition = self.binary(4)
        if self.peek() == "?" and self.kind() == "op":
            self.i += 1
            if self.peek() == ":":
                self.i += 1
                return ("cond", condition, condition, self.ternary())
            then = self.expression()
            self.expect(":")
            return ("cond", condition, then, self.ternary())
        return condition

    def binary(self, minimum):
        left = self.unary()
        while self.kind() == "op" and BINARY.get(self.peek(), 0) >= minimum:
            operator = self.take()
            left = ("bin", operator, left, self.binary(BINARY[operator] + 1))
        return left

    def unary(self):
        token, kind = self.peek(), self.kind()
        if kind == "op" and token in ("!", "~", "-", "+", "*", "&"):
            self.i += 1
            return ("un", token, self.unary())
        if kind == "op" and token in ("++", "--"):
            self.i += 1
            return ("assign", "+=" if token == "++" else "-=", self.unary(), ("num", 1))
        if kind == "id" and token == "sizeof":
            self.i += 1
            if self.peek() == "(":
                close = self.matching_paren(self.i)
                self.i = close + 1
            else:
                self.unary()
            return ("sizeof",)
        if kind == "op" and token == "(" and self.is_cast():
            close = self.matching_paren(self.i)
            type_words = tuple(t for _, t in self.toks[self.i + 1:close])
            self.i = close + 1
            if self.peek() == "{":
                return ("cast", type_words, self.initializer())
            return ("cast", type_words, self.unary())
        return self.postfix()

    def matching_paren(self, start):
        depth = 0
        for j in range(start, len(self.toks)):
            token = self.toks[j][1]
            if self.toks[j][0] == "op":
                depth += (token in "([{") - (token in ")]}")
                if depth == 0:
                    return j
        raise ParseFailure("unbalanced parenthesis")

    def is_cast(self):
        """A parenthesized type: only type words and stars inside, an operand after, and no variable named inside."""
        close = self.matching_paren(self.i)
        inside = self.toks[self.i + 1:close]
        if not inside or any(kind != "id" and text != "*" for kind, text in inside):
            return False
        words = [text for kind, text in inside if kind == "id"]
        after = self.toks[close + 1] if close + 1 < len(self.toks) else ("eof", "")
        if not (after[0] in ("id", "num", "str") or after[1] in ("(", "&", "*", "!", "~", "-", "{", "+")):
            return False
        pointer = any(text == "*" for _, text in inside)
        typed = any(w in TYPE_KEYWORDS for w in words) or pointer
        if words[-1] in self.variables and not typed:
            return False
        return typed or words[-1].endswith("_t") or words[-1].startswith(("zend_", "php_"))

    def postfix(self):
        node = self.primary()
        while True:
            token, kind = self.peek(), self.kind()
            if kind != "op":
                return node
            if token == "(":
                self.i += 1
                args = []
                if not self.accept(")"):
                    while True:
                        args.append(self.assignment())
                        if self.accept(")"):
                            break
                        self.expect(",")
                node = ("call", node, args)
            elif token == "[":
                self.i += 1
                index = self.expression()
                self.expect("]")
                node = ("index", node, index)
            elif token in (".", "->"):
                self.i += 1
                node = ("member", node, self.take(), token == "->")
            elif token in ("++", "--"):
                self.i += 1
                node = ("post", "+=" if token == "++" else "-=", node)
            else:
                return node

    def primary(self):
        kind, token = self.kind(), self.peek()
        if kind == "eof":
            raise ParseFailure("unexpected end")
        if kind == "num":
            self.i += 1
            value = parse_number(token)
            return ("num", value) if value is not None else ("unknown",)
        if kind == "str":
            self.i += 1
            joined = token
            while self.kind() == "str":
                joined += self.take()
            return ("str", joined)
        if kind == "id":
            self.i += 1
            return ("name", token)
        if token == "(":
            if self.peek(1) == "{":
                self.i += 2
                block = self.block_rest()
                self.expect(")")
                return ("stmtexpr", block)
            self.i += 1
            node = self.expression()
            self.expect(")")
            return node
        if token == "{":
            return self.initializer()
        raise ParseFailure(f"unexpected {token!r}")


def parse_body(text, variables=()):
    """The ("block", statements) of one braced function body; a ParseFailure when its outer structure is unreadable."""
    return BodyParser(text, variables).body()


def parse_expression(text, variables=()):
    parser = BodyParser(text, variables)
    node = parser.expression()
    if parser.i != len(parser.toks):
        raise ParseFailure("text after the expression")
    return node
