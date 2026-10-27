"""C macro expansion of the function-defining invocations of a php-src checkout (design-extraction-handlers.md)."""

import re

from php_src_c.source import IDENTIFIER, matching, split_arguments

# The handler-defining macros of the Zend API and the C function each defines (zend_API.h, zend_frameless_function.h).
HANDLER_MACROS = {
    "ZEND_FUNCTION": "zif_{0}", "PHP_FUNCTION": "zif_{0}",
    "ZEND_METHOD": "zim_{0}_{1}", "PHP_METHOD": "zim_{0}_{1}",
    "ZEND_NAMED_FUNCTION": "{0}", "PHP_NAMED_FUNCTION": "{0}",
    "ZEND_FRAMELESS_FUNCTION": "zflf_{0}_{1}",
    "PHP_MINIT_FUNCTION": "zm_startup_{0}", "ZEND_MINIT_FUNCTION": "zm_startup_{0}",
}


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
