"""Source index of the handler extraction: table declarations, the handler struct layout, enumerators, and the
compiled bodies of the functions of one php-src checkout (design-extraction-handlers.md)."""

import collections
import re
from contextlib import contextmanager
from dataclasses import dataclass
from collections.abc import Iterable

import php_src
from php_src_c.definitions import ParseFailure, ParsedBlock, parse_body, parse_expression
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
IMPLICIT_BRANCH = -1
CONFIGURATION_PREFIX = "configuration:"


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

    def inline(self, block, source):
        """The compiled code of a statement expression: its last expression statement becomes the returned value."""
        compiled = self.compiled.get(id(block))
        if compiled is None:
            statements = list(block[1])
            if statements and statements[-1][0] == "expr":
                statements[-1] = ("return", statements[-1][1])
            compiled = self.compiled[id(block)] = Compiler(source.otherwise).compile(ParsedBlock(statements, block.opaque))
        return compiled

    def compile(self, definition):
        text = self.pre.expand(definition.body, definition.source, self.disabled)
        try:
            block = parse_body(text, definition.params)
        except ParseFailure as failure:
            return Compiled([], {}, set(), str(failure))
        return Compiler(definition.source.otherwise).compile(block)


def declarator_name(member):
    names = re.findall(r"[A-Za-z_]\w*", re.sub(r"\[[^\]]*\]", "", member))
    return names[-1]


# ---------------------------------------------------------------------------------------------------------------------
# Compiler: statements to a flat instruction list, so goto, switch fall-through and loops are plain jumps.


@dataclass(frozen=True)
class Local:
    """One lexical declaration, independently of any same-named ancestor or sibling."""

    name: str
    array: bool
    words: tuple[str, ...]
    scope: int


@dataclass(frozen=True)
class Configuration:
    """The source alternative selected for a conditional group, stored in its block's regions."""

    name: str
    scope: int
    group: int


@dataclass(frozen=True)
class ConditionalBinding:
    """A source group's alternative bindings, including the enclosing binding when no branch declares it."""

    configuration: Configuration
    branches: tuple[tuple[int, "Binding"], ...]
    enclosing: "Binding"


Binding = Local | ConditionalBinding | None
Bindings = dict[str, Binding]
Syntax = str | int | None | Configuration | tuple["Syntax", ...] | list["Syntax"]
Branch = tuple[int, Bindings, list[Syntax]]


def reference_children(value: Syntax) -> list[Syntax]:
    match value:
        case ("cast", _, expression):
            return [expression]
        case ("d", _, _, dimensions, expression, _):
            return [*dimensions, expression]
        case ("decl", _, entries):
            return [expression for _, _, dimensions, initial in entries for expression in (*dimensions, initial)]
        case ("init", entries):
            return [expression for _, expression, _ in entries]
    return list(value) if isinstance(value, (tuple, list)) else []


def referenced_names(value: Syntax) -> frozenset[str]:
    pending, names = [value], set()
    while pending:
        node = pending.pop()
        if not isinstance(node, (tuple, list)):
            continue
        if isinstance(node, tuple) and len(node) == 2 and node[0] == "name" and isinstance(node[1], str):
            names.add(node[1])
        elif isinstance(node, tuple) and len(node) == 2 and node[0] == "sizeof":
            names.update(node[1])
        else:
            pending.extend(reference_children(node))
    return frozenset(names)


def binding_configurations(bindings: Iterable[Binding]) -> set[Configuration]:
    pending, seen, configurations = list(bindings), set(), set()
    while pending:
        binding = pending.pop()
        if not isinstance(binding, ConditionalBinding) or id(binding) in seen:
            continue
        seen.add(id(binding))
        configurations.add(binding.configuration)
        pending.extend(local for _, local in binding.branches)
        pending.append(binding.enclosing)
    return configurations


def branch_dependency(node: Syntax) -> bool:
    match node:
        case ("name", _) | ("sizeof", _) | ("call", _, _) | ("opaque", _) | ("unknown",):
            return True
        case ("cgroup", _, _) | ("assign", _, _, _) | ("post", _, _) | ("index", _, _) | ("member", _, _, _):
            return True
        case ("un", "*" | "&", _):
            return True
    return False


def independent_branch(value: Syntax) -> bool:
    pending = [value]
    while pending:
        node = pending.pop()
        if not isinstance(node, (tuple, list)):
            continue
        if branch_dependency(node):
            return False
        pending.extend(reference_children(node))
    return True


def conditional_bindings(configuration: Configuration, branches: list[Branch],
                         enclosing: Bindings) -> Bindings:
    visible = enclosing.copy()
    if not branches:
        return visible
    equivalent = all(body == branches[0][2] for _, _, body in branches) and independent_branch(branches[0][2])
    names = dict.fromkeys(name for _, bindings, _ in branches for name in bindings)
    for name in names:
        before = enclosing.get(name)
        choices = tuple((number, bindings.get(name)) for number, bindings, _ in branches)
        first = choices[0][1]
        if equivalent and isinstance(first, Local) and all(local == first for _, local in choices):
            visible[name] = first
        elif any(local != before for _, local in choices):
            explicit = tuple((number, local) for number, local in choices if number != IMPLICIT_BRANCH)
            visible[name] = ConditionalBinding(configuration, explicit, before)
    return visible


class Instruction(tuple):
    """An instruction with its source-position bindings and the scopes that own its live locals."""

    def __new__(cls, instruction, bindings, scopes):
        value = super().__new__(cls, instruction)
        value.bindings, value.scopes = bindings, scopes
        names = referenced_names(instruction) if any(isinstance(local, ConditionalBinding) for local in bindings.values()) else ()
        value.conditional = tuple(name for name in sorted(names) if isinstance(bindings.get(name), ConditionalBinding))
        return value


class Compiler:
    """Compile a parsed body. Instructions: ("x", expr), ("d", name, pointer, dims, init, type), ("b", cond, then, else),
    ("j", pc), ("r", expr), ("s", subject, cases, default, end), ("g", group, branches, end, configuration), ("o", text),
    ("n",)."""

    def __init__(self, otherwise=()):
        self.instrs, self.labels, self.heads, self.jumps = [], {}, set(), []
        self.switches = []
        self.bindings, self.scopes = {}, []
        self.otherwise = frozenset(otherwise)

    def compile(self, block):
        self.statement(block, None, None)
        self.emit("r", None)
        for pc, label in self.jumps:
            if label not in self.labels:
                return Compiled([], {}, set(), f"goto to unknown label {label}")
            self.replace(pc, "j", self.labels[label])
        self.retain_configurations()
        return Compiled(self.instrs, self.labels, self.heads, opaque=block.opaque)

    def retain_configurations(self) -> None:
        required = binding_configurations(instruction.bindings[name]
                                          for instruction in self.instrs for name in instruction.conditional)
        for pc, instruction in enumerate(self.instrs):
            if instruction[0] != "g":
                continue
            configuration = instruction[4]
            if configuration is not None and configuration not in required:
                instruction.scopes[-1].remove(configuration)
                self.replace(pc, *instruction[:4], None)

    def emit(self, *instruction):
        self.instrs.append(Instruction(instruction, self.bindings, tuple(self.scopes)))
        return len(self.instrs) - 1

    def replace(self, pc, *instruction):
        old = self.instrs[pc]
        self.instrs[pc] = Instruction(instruction, old.bindings, old.scopes)

    @contextmanager
    def scope(self):
        enclosing = self.bindings
        self.scopes.append([])
        try:
            yield
        finally:
            self.scopes.pop()
            self.bindings = enclosing

    def here(self):
        return len(self.instrs)

    def statement(self, node, breaks, continues):
        getattr(self, "s_" + node[0])(node, breaks, continues)

    def s_block(self, node, breaks, continues):
        with self.scope():
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
            local = Local(name, bool(dims), node[1], id(self.scopes[-1]))
            self.scopes[-1].append(local)
            self.bindings = {**self.bindings, name: local}
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
        self.replace(branch, "b", node[1], then, otherwise)
        self.replace(skip, "j", end)

    def s_while(self, node, breaks, continues):
        head = self.emit("n")
        self.heads.add(head)
        branch = self.emit("b", node[1], None, None)
        body = self.here()
        exits, again = [], []
        self.statement(node[2], exits, again)
        self.emit("j", head)
        end = self.emit("n")
        self.replace(branch, "b", node[1], body, end)
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
        with self.scope():
            self.for_loop(node, breaks, continues)

    def for_loop(self, node, breaks, continues):
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
        self.replace(branch, "b", condition if condition else ("num", 1), start, end)
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
        self.replace(switch, "s", node[1], collected["cases"], collected["default"], end)
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
        starts, jumps, branches = [], [], []
        enclosing = self.bindings
        for number, statements in node[2]:
            self.bindings = enclosing
            starts.append((number, self.here()))
            for child in statements:
                self.statement(child, breaks, continues)
            branches.append((number, self.bindings, statements))
            jumps.append(self.emit("j", None))
        configuration = self.group_bindings(node[1], branches, enclosing)
        end = self.emit("n")
        self.patch(jumps, end)
        self.replace(group, "g", node[1], starts, end, configuration)

    def group_bindings(self, group: int, branches: list[Branch],
                       enclosing: Bindings) -> Configuration | None:
        configuration = Configuration(f"{CONFIGURATION_PREFIX}{group}", id(self.scopes[-1]), group)
        if group not in self.otherwise:
            branches = [*branches, (IMPLICIT_BRANCH, enclosing, [])]
        self.bindings = conditional_bindings(configuration, branches, enclosing)
        if self.bindings != enclosing:
            self.scopes[-1].append(configuration)
            return configuration
        return None

    def patch(self, pcs, target):
        for pc in pcs:
            self.replace(pc, "j", target)
