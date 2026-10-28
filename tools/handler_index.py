"""Source index of the handler extraction: table declarations, the handler struct layout, enumerators, and the
compiled bodies of the functions of one php-src checkout (design-extraction-handlers.md)."""

import collections
import re

import php_src
from php_src_c.definitions import ParseFailure, parse_body, parse_expression
from handler_requests import tag_values
from handler_values import arithmetic
from php_src_c.source import matching, split_arguments

STRUCT_TYPE = "zend_object_handlers"

# ---------------------------------------------------------------------------------------------------------------------
# Source index: tables, constants, functions and compiled bodies of the checkout.
TABLE_DECLARATION = re.compile(r"\bzend_object_handlers\s+(?:const\s+)?(\w+)\s*(\[[^\]]*\])?\s*(=|;|,)")
ENUM_BODY = re.compile(r"\benum\b[^{};()]*\{([^{}]*)\}")
TYPEDEF_STRUCT = re.compile(r"\btypedef\s+struct\s+(\w+)\s+(\w+)\s*;")
OBJECT_STRUCT = re.compile(r"\bstruct\s*(\w+)?\s*\{\s*(?:/\*.*?\*/\s*)*zend_object\s+(\w+)\s*;", re.S)
STRUCT_BODY = re.compile(r"struct\s+_zend_object_handlers\s*\{([^{}]*)\}")
INITIALIZER_TYPES = {STRUCT_TYPE}
# Names the machine implements itself; the macro expander leaves them unexpanded.
PRIMITIVES = {
    "EG", "XtOffsetOf", "offsetof", "__builtin_offsetof", "EXPECTED", "UNEXPECTED", "LIKELY", "UNLIKELY", "__builtin_expect", "ZEND_ASSERT", "ZEND_ASSUME",
    "ZEND_UNREACHABLE", "assert", "memcpy", "memmove", "memset", "zend_string_init_interned", "zend_object_std_init",
    "zend_objects_new", "zend_object_alloc", "zend_register_internal_class_with_flags",
    "zend_register_internal_interface", "emalloc", "ecalloc", "pemalloc", "pecalloc", "malloc", "calloc",
    "safe_emalloc", "safe_pemalloc", "emalloc_large", "zval_ptr_dtor", "zval_ptr_dtor_nogc", "zval_dtor",
    "convert_to_string", "convert_to_long", "convert_to_double", "convert_to_boolean", "convert_to_array",
    "convert_to_object", "convert_to_null", "convert_scalar_to_number", "_convert_to_string", "zend_clear_exception",
    "zend_call_known_instance_method", "zend_call_known_instance_method_with_0_params",
    "zend_call_known_instance_method_with_1_params", "zend_call_known_instance_method_with_2_params",
    "zend_error_noreturn", "zend_bailout", "abort", "sizeof", "efree", "efree_size", "efree_large", "efree_huge", "pefree",
    "pefree_size",
}
THROWERS = re.compile(
    r"zend_throw_\w+|zend_(?:type|value|argument\w*|illegal\w*)_error|php_com_throw_exception|zend_error_exception"
    r"|zend_wrong_\w+|zend_zval_type_error|zend_cannot_pass_by_reference|zend_unsupported_operand\w*"
)
NORETURN = {"zend_error_noreturn", "zend_bailout", "abort", "ZEND_UNREACHABLE"}


def is_primitive(name):
    return name in PRIMITIVES or bool(THROWERS.fullmatch(name))


class TableDeclaration:
    """One declaration of a zend_object_handlers variable at file scope."""

    def __init__(self, name, source, static, extern, initializer):
        self.name, self.source, self.static, self.extern, self.initializer = name, source, static, extern, initializer

    def region(self):
        return f"g:{self.source.relative}:{self.name}" if self.static else f"g:{self.name}"


class Compiled:
    """The flat instruction list of one function body and the labels, loop heads and parse status it came with."""

    def __init__(self, instrs, labels, heads, failure=None, opaque=False):
        self.instrs, self.labels, self.heads, self.failure = instrs, labels, heads, failure
        self.opaque = opaque


class Index:
    """Everything the machine reads from the checkout besides function bodies: table declarations, the struct layout,
    enumerators, and the compiled body of each function."""

    def __init__(self, program):
        self.program, self.pre = program, program.preprocessor
        self.fields = self.layout()
        self.tags = tag_values(self.pre)
        self.tables = collections.defaultdict(list)
        for source in program.sources:
            self.scan_tables(source)
        self.embedded = self.embedded_objects()
        self.enumerators = {}
        for source in program.sources:
            for body in ENUM_BODY.findall(source.text):
                self.read_enumerators(body, source)
        self.compiled = {}
        self.macro_names = {
            name for table in list(self.pre.locals.values()) + [self.pre.headers] for name in table if is_primitive(name)
        }
        self.disabled = frozenset(self.macro_names | PRIMITIVES)

    def layout(self):
        for source in self.program.sources:
            found = STRUCT_BODY.search(source.text)
            if found:
                return [declarator_name(member) for member in found.group(1).split(";") if member.strip()]
        raise php_src.ExtractionFailure("zend_object_handlers: no struct declaration in the checkout")

    def embedded_objects(self):
        """The name of the zend_object member that opens a struct, for each struct name and typedef name."""
        found = {}
        for source in self.program.sources:
            for match in OBJECT_STRUCT.finditer(source.text):
                names = {match.group(1)} - {None}
                end = matching(source.text, source.text.index("{", match.start()), "{", "}")
                alias = re.match(r"\s*(\w+)\s*;", source.text[end + 1:])
                names |= {alias.group(1)} if alias else set()
                found.update({name: match.group(2) for name in names})
        for source in self.program.sources:
            for tag, alias in TYPEDEF_STRUCT.findall(source.text):
                if tag in found:
                    found[alias] = found[tag]
        return found

    def scan_tables(self, source):
        text = source.text
        if STRUCT_TYPE not in text:
            return
        for found in TABLE_DECLARATION.finditer(text):
            before = text[:found.start()]
            if before.count("{") != before.count("}"):
                continue
            line = before[before.rfind("\n") + 1:]
            static, extern = bool(re.search(r"\bstatic\b", line)), bool(re.search(r"\bextern\b", line))
            initializer = None
            if found.group(3) == "=":
                brace = text.find("{", found.end())
                initializer = text[brace:matching(text, brace, "{", "}") + 1] if brace >= 0 else None
            if "(" in line or found.group(2) is not None:
                continue
            self.tables[found.group(1)].append(TableDeclaration(found.group(1), source, static, extern, initializer))
            for name in self.listed_names(text, found):
                self.tables[name].append(TableDeclaration(name, source, static, extern, None))

    @staticmethod
    def listed_names(text, found):
        """The further tables a declaration of several declarators names (``static zend_object_handlers a, b;``)."""
        if found.group(3) != ",":
            return []
        rest = text[found.end():text.index(";", found.end())]
        return [name for name in (part.strip() for part in split_arguments(rest)) if name.isidentifier()]

    def read_enumerators(self, body, source):
        value = -1
        for member in split_arguments(body):
            name, _, expression = (part.strip() for part in member.partition("="))
            if not name.isidentifier():
                continue
            value = self.fold(expression, source) if expression else value + 1
            if value is None:
                return
            self.enumerators.setdefault(name, value)

    def fold(self, text, source):
        """The integer an expression of constants denotes, or None."""
        try:
            return self.fold_node(parse_expression(self.pre.expand(text, source, frozenset())), source)
        except (ParseFailure, RecursionError):
            return None

    def fold_node(self, node, source):
        kind = node[0]
        if kind == "num":
            return node[1]
        if kind == "name":
            return self.enumerators.get(node[1])
        if kind == "cast":
            return self.fold_node(node[2], source)
        if kind == "un":
            operand = self.fold_node(node[2], source)
            return None if operand is None else {"-": -operand, "+": operand, "~": ~operand, "!": int(not operand)}.get(node[1])
        if kind == "bin":
            left, right = self.fold_node(node[2], source), self.fold_node(node[3], source)
            return None if left is None or right is None else arithmetic(node[1], left, right)
        return None

    def constant(self, name, source):
        """The integer a macro or enumerator name denotes in a file."""
        if name in self.enumerators:
            return self.enumerators[name]
        macro = self.pre.lookup(source, name)
        return self.fold(macro[1], source) if macro and macro[0] is None else None

    def table_region(self, name, source):
        """The region of a file-scope table visible from a file, or None when no table has that name."""
        declarations = self.tables.get(name)
        if not declarations:
            return None
        for declaration in declarations:
            if declaration.static and declaration.source is source:
                return declaration.region()
        shared = [d for d in declarations if not d.static]
        return shared[0].region() if shared else declarations[0].region()

    def definitions(self, name, source):
        """The definitions a function name reaches from a file: the file's own first, else every visible one."""
        found = [d for d in self.program.functions.get(name, ()) if not d.is_macro]
        local = [d for d in found if d.source is source]
        return local or [d for d in found if d.source.is_header or not d.is_static]

    def code(self, definition):
        compiled = self.compiled.get(id(definition))
        if compiled is None:
            compiled = self.compiled[id(definition)] = self.compile(definition)
        return compiled

    def inline(self, block):
        """The compiled code of a statement expression: its last expression statement becomes the returned value."""
        compiled = self.compiled.get(id(block))
        if compiled is None:
            statements = list(block[1])
            if statements and statements[-1][0] == "expr":
                statements[-1] = ("return", statements[-1][1])
            compiled = self.compiled[id(block)] = Compiler().compile(("block", statements))
        return compiled

    def compile(self, definition):
        text = self.pre.expand(definition.body, definition.source, self.disabled)
        try:
            block = parse_body(text, definition.params)
        except ParseFailure as failure:
            return Compiled([], {}, set(), str(failure))
        return Compiler().compile(block)


def declarator_name(member):
    names = re.findall(r"[A-Za-z_]\w*", re.sub(r"\[[^\]]*\]", "", member))
    return names[-1]


# ---------------------------------------------------------------------------------------------------------------------
# Compiler: statements to a flat instruction list, so goto, switch fall-through and loops are plain jumps.


def contains_opaque(block):
    """Whether the parsed body contains an opaque statement, including a nested statement expression."""
    pending = [block]
    while pending:
        node = pending.pop()
        if not isinstance(node, (tuple, list)):
            continue
        if node and node[0] == "opaque":
            return True
        pending.extend(node)
    return False


class Compiler:
    """Compile a parsed body. Instructions: ("x", expr), ("d", name, pointer, dims, init, type), ("b", cond, then, else),
    ("j", pc), ("r", expr), ("s", subject, cases, default, end), ("g", group, branches, end, exhaustive), ("o", text),
    ("n",)."""

    def __init__(self):
        self.instrs, self.labels, self.heads, self.jumps = [], {}, set(), []
        self.switches = []

    def compile(self, block):
        self.statement(block, None, None)
        self.emit("r", None)
        for pc, label in self.jumps:
            if label not in self.labels:
                return Compiled([], {}, set(), f"goto to unknown label {label}")
            self.instrs[pc] = ("j", self.labels[label])
        return Compiled(self.instrs, self.labels, self.heads, opaque=contains_opaque(block))

    def emit(self, *instruction):
        self.instrs.append(instruction)
        return len(self.instrs) - 1

    def here(self):
        return len(self.instrs)

    def statement(self, node, breaks, continues):
        getattr(self, "s_" + node[0])(node, breaks, continues)

    def s_block(self, node, breaks, continues):
        for child in node[1]:
            self.statement(child, breaks, continues)

    def s_empty(self, node, breaks, continues):
        pass

    def s_expr(self, node, breaks, continues):
        self.emit("x", node[1])

    def s_opaque(self, node, breaks, continues):
        self.emit("o", node[1])

    def s_decl(self, node, breaks, continues):
        for name, pointer, dims, init in node[2]:
            self.emit("d", name, pointer, dims, init, node[1])

    def s_if(self, node, breaks, continues):
        branch = self.emit("b", node[1], None, None)
        then = self.here()
        self.statement(node[2], breaks, continues)
        skip = self.emit("j", None)
        otherwise = self.here()
        if node[3] is not None:
            self.statement(node[3], breaks, continues)
        end = self.emit("n")
        self.instrs[branch] = ("b", node[1], then, otherwise)
        self.instrs[skip] = ("j", end)

    def s_while(self, node, breaks, continues):
        head = self.emit("n")
        self.heads.add(head)
        branch = self.emit("b", node[1], None, None)
        body = self.here()
        exits, again = [], []
        self.statement(node[2], exits, again)
        self.emit("j", head)
        end = self.emit("n")
        self.instrs[branch] = ("b", node[1], body, end)
        self.patch(exits, end)
        self.patch(again, head)

    def s_do(self, node, breaks, continues):
        head = self.emit("n")
        self.heads.add(head)
        exits, again = [], []
        self.statement(node[1], exits, again)
        test = self.here()
        end = self.here() + 1
        self.emit("b", node[2], head, end)
        self.emit("n")
        self.patch(exits, end)
        self.patch(again, test)

    def s_for(self, node, breaks, continues):
        _, init, condition, step, body = node
        self.statement(init, breaks, continues)
        head = self.emit("n")
        self.heads.add(head)
        branch = self.emit("b", condition if condition else ("num", 1), None, None)
        start = self.here()
        exits, again = [], []
        self.statement(body, exits, again)
        advance = self.here()
        if step is not None:
            self.emit("x", step)
        self.emit("j", head)
        end = self.emit("n")
        self.instrs[branch] = ("b", condition if condition else ("num", 1), start, end)
        self.patch(exits, end)
        self.patch(again, advance)

    def s_switch(self, node, breaks, continues):
        switch = self.emit("s", node[1], None, None, None)
        collected = {"cases": [], "default": None}
        self.switches.append(collected)
        exits = []
        self.statement(node[2], exits, continues)
        self.switches.pop()
        end = self.emit("n")
        self.instrs[switch] = ("s", node[1], collected["cases"], collected["default"], end)
        self.patch(exits, end)

    def s_case(self, node, breaks, continues):
        self.switches[-1]["cases"].append((node[1], self.here()))
        self.emit("n")

    def s_default(self, node, breaks, continues):
        self.switches[-1]["default"] = self.here()
        self.emit("n")

    def s_break(self, node, breaks, continues):
        breaks.append(self.emit("j", None))

    def s_continue(self, node, breaks, continues):
        continues.append(self.emit("j", None))

    def s_return(self, node, breaks, continues):
        self.emit("r", node[1])

    def s_goto(self, node, breaks, continues):
        self.jumps.append((self.emit("j", None), node[1]))

    def s_label(self, node, breaks, continues):
        self.labels[node[1]] = self.here()
        self.heads.add(self.here())
        self.emit("n")

    def s_cgroup(self, node, breaks, continues):
        group = self.emit("g", node[1], None, None, None)
        starts, jumps = [], []
        for number, statements in node[2]:
            starts.append((number, self.here()))
            for child in statements:
                self.statement(child, breaks, continues)
            jumps.append(self.emit("j", None))
        end = self.emit("n")
        self.patch(jumps, end)
        self.instrs[group] = ("g", node[1], starts, end, None)

    def patch(self, pcs, target):
        for pc in pcs:
            self.instrs[pc] = ("j", target)
