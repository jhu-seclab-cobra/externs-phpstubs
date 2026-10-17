#!/usr/bin/env python3
"""Give the generated function and method entries the exception classes their php-src implementation may throw
(design-extraction.md, extract_throws.py; algorithm: spec-throws.md).

Reads every C source and header of one php-src checkout outside test
directories, maps each builtin function and method to its C handlers through
the ``*_arginfo.h`` function entry tables, and computes for every C function
and function-like macro a summary of the exception classes it may throw: a
fixpoint over the strongly connected components of the call graph, with
calls into argument binding, user code, diagnostics, and value conversion as
boundaries. Writes the ``throws`` line of every generated entry whose
handlers resolve to classes alone, every other line untouched; an entry whose
handlers throw an object the caller supplies keeps no line and is listed.
A second run over its own output changes nothing.
"""

import argparse
import collections
import re
import sys
from pathlib import Path

import php_src

TOOL = "tools/extract_throws.py"
CALLABLE_KINDS = ("function", "method")
THROWS_LINE = re.compile(r"^  throws: .*\n", re.M)
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
ASSIGNMENT = re.compile(r"\b([A-Za-z_]\w*)\s*=(?!=)")
RETURN = re.compile(r"\breturn\b")
IF = re.compile(r"\bif\s*\(")
ELSE = re.compile(r"\s*else\b")
FUNCTION_TABLE = re.compile(r"\bzend_function_entry\s+(\w+)\s*\[\s*\]\s*=\s*\{")
FRAMELESS_TABLE = re.compile(r"\bzend_frameless_function_info\s+(\w+)\s*\[\s*\]\s*=\s*\{")
REGISTERED_CLASS = re.compile(r"\b(\w+)\s*=\s*(register_class_\w+)\s*\(")
CAST = re.compile(r"^\(\s*(?:const\s+)?(?:struct\s+)?\w+\s*\**\s*\)\s*")
LINKAGE_BLOCK = re.compile(r"\bextern\s+__STR_\d+__\s*$")

# C keywords and operators spelled like calls.
NOT_CALLS = {
    "if", "while", "for", "switch", "return", "sizeof", "do", "else", "case", "defined", "__attribute__",
    "typeof", "_Alignof", "offsetof", "__typeof__", "__builtin_expect", "EXPECTED", "UNEXPECTED",
}
# The handler-defining macros of the Zend API and the C function each defines (zend_API.h, zend_frameless_function.h).
HANDLER_MACROS = {
    "ZEND_FUNCTION": "zif_{0}", "PHP_FUNCTION": "zif_{0}",
    "ZEND_METHOD": "zim_{0}_{1}", "PHP_METHOD": "zim_{0}_{1}",
    "ZEND_NAMED_FUNCTION": "{0}", "PHP_NAMED_FUNCTION": "{0}",
    "ZEND_FRAMELESS_FUNCTION": "zflf_{0}_{1}",
}
# Function entry macros of the arginfo tables: the PHP name and the handler (zend_API.h).
ENTRY_MACROS = {"ZEND_FE", "ZEND_ME", "ZEND_RAW_FENTRY"}
METHOD_MACRO = "ZEND_ME"
ENTRY_END = "ZEND_FE_END"
# Primitives that throw an instance of a class given as an argument: (class argument, class of NULL) (zend_exceptions.c).
CLASS_THROWS = {
    "zend_throw_exception_zstr": (0, "Exception"),
    "zend_throw_error": (0, "Error"),
    "zend_replace_error_handling": (1, "Exception"),
}
# zend_replace_error_handling converts later diagnostics into throws only in this mode (zend.c).
THROW_MODE = ("zend_replace_error_handling", 0, "EH_THROW")
# Primitives that throw an object given as an argument; NULL rethrows the pending exception (zend_exceptions.c).
OBJECT_THROWS = {"zend_throw_exception_object": 0, "zend_throw_exception_internal": 0}
# The primitive initializing a new object of a class into a zval: (object argument, class argument) (zend_API.c).
OBJECT_CREATION = ("object_init_ex", 0, 1)
# Argument binding: the parameter parsing API (zend_API.h).
BINDING_PREFIXES = (
    "ZEND_PARSE_PARAMETERS", "Z_PARAM_", "Z_FLF_PARAM_", "zend_parse_arg", "zend_parse_parameters",
    "zend_parse_method_parameters", "zend_wrong_parameter", "zend_wrong_callback",
)
# Binding specifiers that check a value beyond its declared type, and the class they throw (zend_API.h).
SPECIFIER_MACROS = (("Z_PARAM_PATH", "ValueError"), ("Z_PARAM_CLASS", "TypeError"))
FORMAT_SPECIFIERS = {"p": "ValueError", "P": "ValueError", "C": "TypeError"}
# The format string argument of each parsing function (zend_API.h).
FORMAT_ARGUMENT = {"zend_parse_parameters": 1, "zend_parse_parameters_ex": 2, "zend_parse_method_parameters": 2}
# The calls that run user code: the executor, functions, constant expressions, generators, and fibers (zend_execute.h,
# zend_execute_API.c, zend_ast.h, zend_generators.c, zend_fibers.c).
USER_CODE = {
    "execute_ex", "zend_execute", "zend_call_function", "zend_ast_evaluate_ex", "zend_generator_resume",
    "zend_fiber_switch_context", "zend_fiber_delegate_transfer_result",
}
# Diagnostics; a throw they cause under EH_THROW is attributed to zend_replace_error_handling (zend.c, main.c).
DIAGNOSTIC_PREFIXES = ("zend_error", "php_error_docref")
DIAGNOSTICS = {"php_verror"}
# Value conversion: the conversion API zend_operators.h declares, matched by these prefixes, and the truth tests.
CONVERSION_HEADER = Path("Zend/zend_operators.h")
CONVERSION_PREFIXES = ("convert_", "_convert_", "_try_convert_", "try_convert_", "zval_get_", "zval_try_get_",
                       "_zval_get_", "_zval_try_get_")
TRUTH_TESTS = {"zend_is_true", "zend_object_is_true", "i_zend_is_true", "zval_is_true"}
TRUE_LITERALS, FALSE_LITERALS = {"true", "1"}, {"false", "0", "NULL", "nullptr"}
NULL_LITERALS = {"NULL", "nullptr", "0"}
OBJECT_ACCESSORS = re.compile(r"^(?:Z_OBJ_P|Z_OBJ)\s*\((.*)\)$", re.S)
CLASS_OF_OBJECT = re.compile(r"^(?:Z_OBJCE_P|Z_OBJCE)\s*\((.*)\)$", re.S)

# Summary element kinds (spec-throws.md): an object no class set bounds is open; a class expression no rule resolves is
# unresolved, and fails the run when it reaches an entry.
CLASS, CLASS_PARAM, OBJECT_PARAM, OPEN, UNRESOLVED = "class", "class_param", "object_param", "open", "unresolved"
# The argument expression of a function reference, whose call site is not in the body; it resolves to no class.
UNKNOWN_ARGUMENT = "__ARGUMENT__"
# A function named as a value; an operand of an equality test is compared, never passed on to be called.
# A local declaration at the start of a statement: a type name, pointer marks, and the declared name.
LOCAL_DECLARATION = re.compile(r"(?:^|[{;}])\s*(?:(?:const|static|struct|unsigned|signed|volatile)\s+)*[A-Za-z_]\w*\s*[\s*]\s*\**\s*([A-Za-z_]\w*)\s*(?=[;,=\[])")
REFERENCE = re.compile(r"(?<![=!]=)(?<![=!]=\s)\b([A-Za-z_]\w*)\b(?!\s*(?:\(|[=!]=))")


class Source:
    """One C file with comments removed, string literals replaced by placeholders, and macros recorded."""

    def __init__(self, path, strings):
        self.path = path
        raw = path.read_text(encoding="utf-8", errors="replace")
        lexed = LEXEME.sub(lambda m: self.lexeme(m.group(0), strings), raw).replace("\\\n", " ")
        lines = balance_conditionals(lexed.split("\n"))
        self.macros = []
        for number, line in enumerate(lines):
            if not line.lstrip().startswith("#"):
                continue
            define = DEFINE.match(line)
            if define:
                params = None if define.group(2) is None else [p.strip() for p in define.group(3).split(",") if p.strip()]
                self.macros.append((define.group(1), params, define.group(4)))
            lines[number] = ""
        self.text = "\n".join(lines)

    @staticmethod
    def lexeme(text, strings):
        if text.startswith("/"):
            return " " + "\n" * text.count("\n")
        if text.startswith("'"):
            return "0"
        strings.append(text[1:-1])
        return f"__STR_{len(strings) - 1}__"


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


class Preprocessor:
    """C macro expansion of the top-level invocations that define functions: a function-like macro whose body
    holds balanced braces and a function body or a handler macro, expanded by the C rules (argument
    pre-expansion, ## pasting, # stringizing, no recursive expansion), so the definitions it emits are read
    like written ones. The handler macros stay unexpanded; definition_head reads them."""

    def __init__(self, sources, strings):
        self.strings, self.headers, self.locals = strings, {}, {}
        for source in sources:
            table = {}
            for name, params, body in source.macros:
                table.setdefault(name, (params, body))
            self.locals[id(source)] = table
            if source.is_header:
                for name, macro in table.items():
                    self.headers.setdefault(name, macro)
        self.defining = {}

    def lookup(self, source, name):
        """The macro a name denotes in a file: its own definition first, else the first header's."""
        if name in HANDLER_MACROS:
            return None
        return self.locals[id(source)].get(name) or self.headers.get(name)

    def defines_functions(self, source, name, visiting=frozenset()):
        macro = self.lookup(source, name)
        if macro is None or macro[0] is None or name in visiting:
            return False
        body = macro[1]
        if body.count("{") != body.count("}"):
            return False
        if "{" in body:
            return True
        return any(n in HANDLER_MACROS or self.defines_functions(source, n, visiting | {name}) for n in IDENTIFIER.findall(body))

    def expand_definitions(self, source):
        """The file text with every top-level invocation of a function-defining macro expanded."""
        text, out, depth, i = source.text, [], 0, 0
        while i < len(text):
            ch = text[i]
            if ch in "{(":
                depth += 1
            elif ch in "})":
                depth -= 1
            match = IDENTIFIER.match(text, i) if depth == 0 and (ch.isalpha() or ch == "_") else None
            if not match or (i and (text[i - 1].isalnum() or text[i - 1] == "_")):
                out.append(ch)
                i += 1
                continue
            invocation = self.invocation(text, match.end()) if self.defines_functions(source, match.group(0)) else None
            if invocation is None:
                out.append(match.group(0))
                i = match.end()
                continue
            args, end = invocation
            out.append(self.expand(self.substitute(source, match.group(0), args, frozenset()), source,
                                   frozenset({match.group(0)})))
            i = end
        source.text = "".join(out)

    @staticmethod
    def invocation(text, start):
        """The arguments and end offset of the parenthesized argument list at or after start, or None."""
        j = start
        while j < len(text) and text[j].isspace():
            j += 1
        if j >= len(text) or text[j] != "(":
            return None
        close = matching(text, j, "(", ")")
        return None if close < 0 else (split_arguments(text[j + 1:close]), close + 1)

    def expand(self, text, source, disabled):
        """Expand every macro in text; a name is not expanded inside its own expansion."""
        i = 0
        while True:
            match = re.compile(r"\b[A-Za-z_]\w*").search(text, i)
            if not match:
                return text
            name = match.group(0)
            macro = None if name in disabled else self.lookup(source, name)
            if macro is None:
                i = match.end()
                continue
            if macro[0] is None:
                replacement, end = self.expand(macro[1], source, disabled | {name}), match.end()
            else:
                invocation = self.invocation(text, match.end())
                if invocation is None:
                    i = match.end()
                    continue
                args, end = invocation
                replacement = self.expand(self.substitute(source, name, args, disabled), source, disabled | {name})
            text = text[:match.start()] + replacement + text[end:]
            i = match.start() + self.rescan_offset(replacement, text[match.start() + len(replacement):], source, disabled)

    def rescan_offset(self, replacement, rest, source, disabled):
        """Where scanning resumes: at a trailing function-like macro name that the following text invokes."""
        tail = re.search(r"([A-Za-z_]\w*)\s*$", replacement)
        if tail and rest.lstrip().startswith("(") and tail.group(1) not in disabled:
            macro = self.lookup(source, tail.group(1))
            if macro and macro[0] is not None:
                return tail.start(1)
        return len(replacement)

    def substitute(self, source, name, args, disabled):
        """The body of a function-like macro with its parameters replaced by the C rules."""
        params, body = self.lookup(source, name)
        values = dict(zip(params, args))
        if params and params[-1] == "...":
            values["__VA_ARGS__"] = ", ".join(args[len(params) - 1:])
        tokens = re.findall(r"##|#|[A-Za-z_]\w*|\s+|.", body.strip(), re.S)
        out = []
        for k, token in enumerate(tokens):
            if token not in values:
                out.append(token)
                continue
            before = next((t for t in reversed(tokens[:k]) if not t.isspace()), "")
            after = next((t for t in tokens[k + 1:] if not t.isspace()), "")
            if before == "#":
                out.pop()
                while out and out[-1].isspace():
                    out.pop()
                self.strings.append(values[token])
                out.append(f"__STR_{len(self.strings) - 1}__")
            elif "##" in (before, after):
                out.append(values[token])
            else:
                out.append(self.expand(values[token], source, disabled))
        return re.sub(r"\s*##\s*", "", "".join(out))


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


def strip_parentheses(expression):
    expression = expression.strip()
    while expression.startswith("(") and matching(expression, 0) == len(expression) - 1:
        expression = expression[1:-1].strip()
    return expression


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


class Program:
    """Every definition of one php-src checkout, with C linkage, class entries, and builtin entries."""

    def __init__(self, root):
        self.strings, self.sources, self.unowned = [], [], set()
        self.functions = collections.defaultdict(list)
        for path in php_src.source_files(root, SOURCE_SUFFIXES):
            source = Source(path, self.strings)
            source.relative, source.is_header = path.relative_to(root), path.suffix == ".h"
            self.sources.append(source)
        preprocessor = Preprocessor(self.sources, self.strings)
        for source in self.sources:
            preprocessor.expand_definitions(source)
            self.load(source)
        self.conversions = conversion_names(root / CONVERSION_HEADER, self.strings)
        self.class_names = self.registered_class_names()
        self.class_entries = {
            variable: self.class_names[register]
            for source in self.sources
            for variable, register in REGISTERED_CLASS.findall(source.text)
            if register in self.class_names
        }

    def load(self, source):
        for found in definitions_of(source):
            self.functions[found.name].append(found)
        for name, params, body in source.macros:
            if params is not None:
                self.functions[name].append(Definition(name, source, params, body, False, False, True))

    def string(self, expression):
        """The value of a string literal expression, adjacent literals and ZEND_NS_NAME joined."""
        parts = STRING_PLACEHOLDER.findall(expression)
        joiner = "\\" if expression.lstrip().startswith("ZEND_NS_NAME") else ""
        return joiner.join(self.strings[int(p)].replace("\\\\", "\\") for p in parts)

    def resolve(self, caller, call):
        """The definitions a call by name reaches: the caller's file first, else every definition visible to it."""
        candidates = self.functions.get(call.name, ())
        if call.args is None:
            candidates = [d for d in candidates if not d.is_macro]
        local = [d for d in candidates if d.source is caller.source]
        return local or [d for d in candidates if d.source.is_header or not d.is_static]

    def registered_class_names(self):
        """register_class_X → the PHP name its INIT_CLASS_ENTRY, INIT_NS_CLASS_ENTRY, or enum registration spells."""
        names = {}
        for name, definitions in self.functions.items():
            if not name.startswith("register_class_"):
                continue
            for definition in definitions:
                spelled = self.registered_name(definition.body)
                if spelled:
                    names[name] = spelled
        return names

    def registered_name(self, body):
        for match in CALL.finditer(body):
            if match.group(1) not in ("INIT_CLASS_ENTRY", "INIT_NS_CLASS_ENTRY", "zend_register_internal_enum"):
                continue
            args = split_arguments(body[match.end():matching(body, match.end() - 1)])
            if match.group(1) == "INIT_CLASS_ENTRY":
                return self.string(args[1])
            if match.group(1) == "INIT_NS_CLASS_ENTRY":
                return self.string(args[1]) + "\\" + self.string(args[2])
            return self.string(args[0])
        return None

    def method_tables(self):
        """Function entry table name → PHP class name, read from every class registration."""
        tables = {}
        for name, definitions in self.functions.items():
            if not name.startswith("register_class_"):
                continue
            for definition in definitions:
                for match in CALL.finditer(definition.body):
                    if match.group(1) in ("INIT_CLASS_ENTRY", "INIT_NS_CLASS_ENTRY", "zend_register_internal_enum"):
                        args = split_arguments(definition.body[match.end():matching(definition.body, match.end() - 1)])
                        tables[args[-1]] = self.class_names[name]
        return tables

    def entries(self):
        """(subject kind, folded subject) → handler names, from every arginfo function entry table; a method entry
        of a table no class registration names is skipped and its table recorded in unowned."""
        tables, entries = self.method_tables(), collections.defaultdict(set)
        for source in self.sources:
            if not source.path.name.endswith("_arginfo.h"):
                continue
            frameless = self.frameless_tables(source)
            for match in FUNCTION_TABLE.finditer(source.text):
                owner = tables.get(match.group(1))
                block = source.text[match.end() - 1:matching_brace(source.text, match.end() - 1)]
                for entry in CALL.finditer(block):
                    if entry.group(1) not in ENTRY_MACROS:
                        if entry.group(1) not in ("ZEND_NS_NAME",):
                            raise php_src.ExtractionFailure(f"{source.relative}: unknown function entry macro {entry.group(1)}")
                        continue
                    if owner is None and entry.group(1) == METHOD_MACRO:
                        self.unowned.add(match.group(1))
                        continue
                    args = split_arguments(block[entry.end():matching(block, entry.end() - 1)])
                    name, handlers = self.entry(entry.group(1), args, frameless)
                    key = ("method", f"{owner}::{name}".lower()) if owner else ("function", name.lower())
                    entries[key] |= handlers
        return entries

    def entry(self, macro, args, frameless):
        if macro == "ZEND_FE":
            return args[0], {f"zif_{args[0]}"}
        if macro == "ZEND_ME":
            return args[1], {f"zim_{args[0]}_{args[1]}"}
        handlers = set() if args[1] == "NULL" else {args[1]}
        return self.string(args[0]), handlers | frameless.get(args[4], set())

    @staticmethod
    def frameless_tables(source):
        tables = {}
        for match in FRAMELESS_TABLE.finditer(source.text):
            block = source.text[match.end() - 1:matching_brace(source.text, match.end() - 1)]
            tables[match.group(1)] = {f"zflf_{n}_{a}" for n, a in re.findall(r"ZEND_FRAMELESS_FUNCTION_NAME\(\s*(\w+)\s*,\s*(\d+)\s*\)", block)}
        return tables


def conversion_names(header, strings):
    text = Source(header, strings).text + "\n".join(f"{n}()" for n, _, _ in Source(header, strings).macros)
    return {n for n in IDENTIFIER.findall(text) if n.startswith(CONVERSION_PREFIXES)} | TRUTH_TESTS


class Summary:
    """What one definition may throw, which classes it creates into its parameters, and which classes it returns."""

    def __init__(self, throws=frozenset(), creates=None, returns=frozenset()):
        self.throws, self.creates, self.returns = throws, creates or {}, returns

    def __eq__(self, other):
        return (self.throws, self.creates, self.returns) == (other.throws, other.creates, other.returns)


EMPTY = Summary()


def element(kind, value, guards=frozenset()):
    return kind, value, guards


class Evaluation:
    """One pass over one definition under the current summaries of its callees."""

    def __init__(self, program, definition, summaries):
        self.program, self.definition, self.summaries = program, definition, summaries
        self.creations, self.creates = collections.defaultdict(set), collections.defaultdict(set)

    def run(self):
        for call in self.definition.calls:
            self.create(call)
        throws = {t for call in self.definition.calls for t in self.throws(call)}
        returns = set()
        if self.definition.returns_class:
            for expression in self.definition.returns:
                returns |= self.class_elements(expression, None)
        return Summary(frozenset(throws), {k: frozenset(v) for k, v in self.creates.items()}, frozenset(returns))

    def callees(self, call):
        return self.program.resolve(self.definition, call)

    def create(self, call):
        """Record the objects a call initializes: by object_init_ex or by a callee creating into a parameter."""
        name, target_index, class_index = OBJECT_CREATION
        if call.args is None:
            return
        if call.name == name:
            self.created(call.argument(target_index, "NULL"), self.class_elements(call.argument(class_index, "NULL"), None))
            return
        if self.is_boundary(call.name):
            return
        for callee in self.callees(call):
            for index, classes in self.summaries.get(id(callee), EMPTY).creates.items():
                if index < len(call.args):
                    self.created(call.args[index], {c for t in classes for c in self.instantiate_class(t, call)})

    def created(self, target, classes):
        variable = object_variable(target)
        index = self.definition.index(variable)
        (self.creates[index] if index is not None else self.creations[variable]).update(classes)

    def is_boundary(self, name):
        return (
            name.startswith(BINDING_PREFIXES) or name in USER_CODE or name in DIAGNOSTICS
            or name.startswith(DIAGNOSTIC_PREFIXES) or name in self.program.conversions
            or name in CLASS_THROWS or name in OBJECT_THROWS or name == OBJECT_CREATION[0]
        )

    def throws(self, call):
        name, guards = call.name, call.guards
        if name in CLASS_THROWS:
            if name == THROW_MODE[0] and call.argument(THROW_MODE[1], "") != THROW_MODE[2]:
                return set()
            index, default = CLASS_THROWS[name]
            return {guarded(t, guards) for t in self.class_elements(call.argument(index, "NULL"), default)}
        if name in OBJECT_THROWS:
            return {guarded(t, guards) for t in self.object_elements(call.argument(OBJECT_THROWS[name], "NULL"))}
        if self.is_boundary(name):
            return {element(CLASS, c, guards) for c in self.specifier_classes(call)}
        found = set()
        for callee in self.callees(call):
            for raised in self.summaries.get(id(callee), EMPTY).throws:
                found |= self.instantiate_raise(raised, call)
        return found

    def specifier_classes(self, call):
        """The classes a binding specifier throws for a value its declared type admits."""
        classes = {cls for prefix, cls in SPECIFIER_MACROS if call.name.startswith(prefix)}
        index = FORMAT_ARGUMENT.get(call.name)
        if index is not None:
            classes |= {FORMAT_SPECIFIERS[c] for c in self.program.string(call.argument(index, "")) if c in FORMAT_SPECIFIERS}
        return classes

    def instantiate_raise(self, raised, call):
        kind, value, callee_guards = raised
        guards = set(call.guards)
        for index, truth in callee_guards:
            argument = strip_parentheses(call.argument(index, ""))
            if argument in TRUE_LITERALS | FALSE_LITERALS:
                if (argument in TRUE_LITERALS) != truth:
                    return set()
                continue
            guard = parameter_guard(argument, self.definition.params)
            if guard:
                guards.add((guard[0], guard[1] == truth))
        if not consistent(guards):
            return set()
        if kind == CLASS_PARAM:
            index, default = value
            elements = self.class_elements(call.argument(index, "NULL"), default)
        elif kind == OBJECT_PARAM:
            elements = self.object_elements(call.argument(value, "NULL"))
        else:
            elements = {element(kind, value)}
        return {guarded(t, frozenset(guards)) for t in elements}

    def instantiate_class(self, class_term, call, seen=frozenset()):
        kind, value, _ = class_term
        if kind != CLASS_PARAM:
            return {class_term}
        index, default = value
        return self.class_elements(call.argument(index, "NULL"), default, seen)

    def class_elements(self, expression, default, seen=frozenset()):
        """The summary elements a class entry expression denotes."""
        expression = strip_casts(expression)
        if expression in seen:
            return set()
        if expression in NULL_LITERALS:
            return {element(CLASS, default)} if default else set()
        index = self.definition.index(expression)
        if index is not None:
            return {element(CLASS_PARAM, (index, default))}
        alternatives = conditional_alternatives(expression)
        if alternatives:
            return {t for e in alternatives for t in self.class_elements(e, default, seen)}
        of_object = CLASS_OF_OBJECT.match(expression)
        if of_object:
            return {t for t in self.object_elements(of_object.group(1)) if t[0] != OBJECT_PARAM} or {
                element(UNRESOLVED, f"{self.definition.name}: {expression}")
            }
        if expression in self.definition.assignments:
            return {t for rhs in self.definition.assignments[expression] for t in self.class_elements(rhs, default, seen | {expression})}
        if expression in self.program.class_entries:
            return {element(CLASS, self.program.class_entries[expression])}
        call = re.match(r"^([A-Za-z_]\w*)\s*\((.*)\)$", expression, re.S)
        inner = call and Call(call.group(1), split_arguments(call.group(2)), frozenset())
        if inner and self.callees(inner):
            return {c for callee in self.callees(inner) for t in self.summaries.get(id(callee), EMPTY).returns for c in self.instantiate_class(t, inner, seen | {expression})}
        return {element(UNRESOLVED, f"{self.definition.name}: {expression}")}

    def object_elements(self, expression):
        """The summary elements an object expression denotes: created classes, a caller's object, or an object no analysis bounds."""
        variable = object_variable(expression)
        if variable in NULL_LITERALS:
            return set()
        if variable in self.creations:
            return set(self.creations[variable])
        index = self.definition.index(variable)
        if index is not None:
            return {element(OBJECT_PARAM, index)}
        return {element(OPEN, f"object {variable}")}


def guarded(found, guards):
    kind, value, own = found
    return kind, value, own | guards


def strip_casts(expression):
    expression = strip_parentheses(expression)
    while CAST.match(expression):
        expression = strip_parentheses(CAST.sub("", expression, count=1))
    return expression


def object_variable(expression):
    expression = strip_casts(expression).lstrip("&").strip()
    accessor = OBJECT_ACCESSORS.match(expression)
    return object_variable(accessor.group(1)) if accessor else strip_casts(expression)


def conditional_alternatives(expression):
    """The two alternatives of a top-level conditional expression, or None."""
    depth, question = 0, None
    for j, ch in enumerate(expression):
        depth += (ch in "([{") - (ch in ")]}")
        if depth == 0 and ch == "?" and question is None:
            question = j
        elif depth == 0 and ch == ":" and question is not None:
            return expression[question + 1:j], expression[j + 1:]
    return None


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


def summarize(program, roots):
    """The fixpoint summary of every definition reachable from the roots."""
    definitions, edges, frontier = {}, {}, list(roots)
    while frontier:
        definition = frontier.pop()
        if id(definition) in definitions:
            continue
        definitions[id(definition)] = definition
        analyze(definition, program.functions)
        callees = [c for call in definition.calls for c in program.resolve(definition, call)]
        edges[id(definition)] = [id(c) for c in callees]
        frontier.extend(callees)
    summaries = {}
    for component in strongly_connected(list(definitions), edges):
        changed = True
        while changed:
            changed = False
            for node in component:
                summary = Evaluation(program, definitions[node], summaries).run()
                if summary != summaries.get(node, EMPTY):
                    summaries[node] = summary
                    changed = True
    return summaries


def handler_definitions(program, entries):
    """Handler name → its definitions; a Handler no definition defines fails the run."""
    handlers = {h: program.functions.get(h, []) for names in entries.values() for h in names}
    undefined = sorted(h for h, found in handlers.items() if not found)
    if undefined:
        raise php_src.ExtractionFailure(f"Handlers no definition defines: {', '.join(undefined)}")
    return handlers


def throws_of(program, entries):
    """(kind, folded subject) → the sorted folded classes its Handlers may throw, or None when one throws an object
    no class set bounds, for every entry with a Handler; a class expression no rule resolves fails the run."""
    handlers = handler_definitions(program, entries)
    summaries = summarize(program, [d for found in handlers.values() for d in found])
    result, unresolved = {}, set()
    for key, names in entries.items():
        if not names:
            continue
        elements = {t for h in names for d in handlers[h] for t in summaries.get(id(d), EMPTY).throws}
        unresolved |= {f"{t[0]} {t[1]}" for t in elements if t[0] not in (CLASS, OPEN)}
        result[key] = None if any(t[0] == OPEN for t in elements) else sorted({t[1].lower() for t in elements})
    if unresolved:
        raise php_src.ExtractionFailure(f"class expressions no rule resolves reach an entry: {'; '.join(sorted(unresolved))}")
    return result


def check_declared(models, throws):
    """Fail when a throws element names a class no generated document declares."""
    classes = php_src.declared(php_src.generated_documents(models))
    undeclared = sorted({c for found in throws.values() if found for c in found if ("class", c) not in classes})
    if undeclared:
        raise php_src.ExtractionFailure(f"throws elements no generated document declares: {', '.join(undeclared)}")


def with_throws(entry, throws):
    """The entry text with its throws line replaced: the classes of its Handlers, or none."""
    text = THROWS_LINE.sub("", entry.text)
    found = throws.get(entry.key()) if entry.kind in CALLABLE_KINDS else None
    return text if found is None else text + f"  throws: [{', '.join(found)}]\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--php-src", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    try:
        program = Program(args.php_src)
        throws = throws_of(program, program.entries())
        check_declared(args.models, throws)
        changed = php_src.rewrite(args.models, lambda entry: with_throws(entry, throws))
    except php_src.ExtractionFailure as failure:
        print(f"{TOOL}: {failure}", file=sys.stderr)
        sys.exit(1)
    opened = sorted(subject for (_, subject), found in throws.items() if found is None)
    print(
        f"{TOOL}: {len(throws)} entries with a Handler, {changed} documents rewritten; "
        f"no throws line (an object the caller supplies): {', '.join(opened)}; "
        f"method tables no class registration names: {', '.join(sorted(program.unowned))}"
    )


if __name__ == "__main__":
    main()
