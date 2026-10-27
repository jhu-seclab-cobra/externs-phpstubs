"""C source text of one php-src checkout: comments, strings and directives removed (design-extraction-handlers.md).

A ``Source`` is one C or C++ file with comments removed, string literals replaced by placeholders, and macro
definitions recorded. The plain view keeps the text of every branch of a conditional group and drops the directives,
so a reader sees all configurations at once. The provenance view keeps one marker per branch of each group, so a
reader that must not overwrite one configuration by another can tell the branches apart.
"""

import re

# The C and C++ sources of php-src; intl and others implement builtins in C++.
SOURCE_SUFFIXES = (".c", ".h", ".cpp", ".cc")

# Comments, string literals, and character literals in one alternation, so the leftmost lexeme wins.
LEXEME = re.compile(r"/\*.*?\*/|//[^\n]*|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'", re.S)
STRING_PLACEHOLDER = re.compile(r"__STR_(\d+)__")
DEFINE = re.compile(r"^[ \t]*#[ \t]*define[ \t]+(\w+)(\(([^)]*)\))?(.*)$")
CONDITIONAL = re.compile(r"^[ \t]*#[ \t]*(if|ifdef|ifndef|elif|elifdef|elifndef|else|endif)\b")
BRACKETS = re.compile(r"[{}()]")
IDENTIFIER = re.compile(r"[A-Za-z_]\w*")
CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
# One conditional branch marker of the provenance view: the group number, then the branch number or END.
BRANCH = re.compile(r"__BRANCH_(\d+)_(\d+|END)__")
DIRECTIVE = re.compile(r"^[ \t]*#[ \t]*(if|ifdef|ifndef|elif|elifdef|elifndef|else|endif)\b(.*)$")


class Source:
    """One C file with comments removed, string literals replaced by placeholders, and macros recorded.

    With provenance, each conditional directive becomes a marker line and ``conditions`` maps (group, branch) to the
    condition the branch stands under and ``otherwise`` holds the groups that end in an else branch; a nested group is
    numbered in order of its opening directive."""

    def __init__(self, path, strings, provenance=False):
        self.path = path
        self.provenance, self.conditions, self.otherwise = provenance, {}, set()
        raw = path.read_text(encoding="utf-8", errors="replace")
        lexed = LEXEME.sub(lambda m: self.lexeme(m.group(0), strings), raw).replace("\\\n", " ")
        lines = balance_conditionals(lexed.split("\n"))
        self.macros = []
        marks = self.branch_markers(lines) if provenance else {}
        for number, line in enumerate(lines):
            if not line.lstrip().startswith("#"):
                continue
            define = DEFINE.match(line)
            if define:
                params = None if define.group(2) is None else [p.strip() for p in define.group(3).split(",") if p.strip()]
                self.macros.append((define.group(1), params, define.group(4)))
            lines[number] = marks.get(number, "")
        self.text = "\n".join(lines)

    def branch_markers(self, lines):
        """Line number → marker for every conditional directive, recording each branch's condition."""
        marks, groups, count = {}, [], 0
        for number, line in enumerate(lines):
            directive = DIRECTIVE.match(line)
            if not directive:
                continue
            keyword, rest = directive.group(1), " ".join(directive.group(2).split())
            if keyword.startswith("if"):
                groups.append([count, []])
                count += 1
            if not groups:
                continue
            group, conditions = groups[-1]
            if keyword == "endif":
                marks[number] = f"__BRANCH_{group}_END__"
                groups.pop()
                continue
            condition = branch_condition(keyword, rest, conditions)
            self.conditions[(group, len(conditions))] = condition
            if keyword == "else":
                self.otherwise.add(group)
            marks[number] = f"__BRANCH_{group}_{len(conditions)}__"
            conditions.append(condition)
        return marks

    @staticmethod
    def lexeme(text, strings):
        if text.startswith("/"):
            return " " + "\n" * text.count("\n")
        if text.startswith("'"):
            return "0"
        strings.append(text[1:-1])
        return f"__STR_{len(strings) - 1}__"


def branch_condition(keyword, rest, earlier):
    """The condition one branch of a group stands under, as text; an else branch negates the branches before it."""
    if keyword in ("if", "elif"):
        return rest
    if keyword in ("ifdef", "elifdef"):
        return f"defined({rest})"
    if keyword in ("ifndef", "elifndef"):
        return f"!defined({rest})"
    return "!(" + " || ".join(earlier) + ")"


def balance_conditionals(lines):
    """Keep every branch of each conditional group; a group whose branches leave brackets open keeps the brackets
    of its first branch only, so the kept text nests as each single configuration does."""
    lines, groups = list(lines), []
    for number, line in enumerate(lines):
        directive = CONDITIONAL.match(line)
        if not directive:
            continue
        keyword = directive.group(1)
        if keyword.startswith("if"):
            groups.append([number])
        elif groups and keyword in ("elif", "else", "elifdef", "elifndef"):
            groups[-1].append(number)
        elif groups and keyword == "endif":
            neutralize(lines, groups.pop() + [number])
    return lines


def neutralize(lines, bounds):
    branches = [range(start + 1, end) for start, end in zip(bounds, bounds[1:])]
    if all(bracket_delta(lines[n] for n in branch) == (0, 0) for branch in branches):
        return
    for branch in branches[1:]:
        for n in branch:
            lines[n] = BRACKETS.sub(" ", lines[n])


def bracket_delta(lines):
    text = "".join(lines)
    return text.count("{") - text.count("}"), text.count("(") - text.count(")")


def matching(text, i, openers="([{", closers=")]}"):
    """The offset of the bracket closing the one at i, or -1."""
    depth = 0
    for j in range(i, len(text)):
        ch = text[j]
        if ch in openers:
            depth += 1
        elif ch in closers:
            depth -= 1
            if depth == 0:
                return j
    return -1


def matching_brace(text, i):
    """The offset of the brace closing the one at i; parentheses split by conditional compilation are not counted."""
    return matching(text, i, "{", "}")


def split_arguments(text):
    """Split an argument list on top-level commas."""
    parts, depth, start = [], 0, 0
    for j, ch in enumerate(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:j].strip())
            start = j + 1
    parts.append(text[start:].strip())
    return [] if parts == [""] else parts


def parameter_name(declaration):
    """The name a C parameter declaration binds, '...' for a variadic tail, or None for void."""
    declaration = declaration.strip()
    if declaration in ("void", ""):
        return None
    if declaration == "...":
        return "__VA_ARGS__"
    pointer = re.search(r"\(\s*\*\s*(\w+)\s*\)", declaration)
    if pointer:
        return pointer.group(1)
    names = IDENTIFIER.findall(re.sub(r"\[[^\]]*\]", "", declaration))
    return names[-1] if names else None


def statement_end(text, start):
    """The offset ending the statement or block starting at or after start."""
    j = start
    while j < len(text) and text[j].isspace():
        j += 1
    if j < len(text) and text[j] == "{":
        end = matching_brace(text, j)
        return len(text) - 1 if end < 0 else end
    depth = 0
    for k in range(j, len(text)):
        ch = text[k]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                return k - 1
        elif ch == ";" and depth == 0:
            return k
    return len(text) - 1


def strip_parentheses(expression):
    expression = expression.strip()
    while expression.startswith("(") and matching(expression, 0) == len(expression) - 1:
        expression = expression[1:-1].strip()
    return expression
