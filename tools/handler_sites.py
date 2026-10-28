"""Handler write sites of the handler extraction (spec-extraction-handlers.md step 3).

Every write of an object's ``handlers`` field in a function of the checkout has a disposition. A write the creation
runs executed is a creation. Any other write is a copy of the table of an object of the same struct type, a write of
named tables to an object of one struct type (a typed write), or a write to the ``handlers`` field of a struct that is
not an object (a foreign write). A typed write gives its tables to every class whose creator allocates that struct
type, because the code that allocates the type is the code that gives the class its objects. A write that fits none
of these fails the extraction.
"""

import collections
import re

import php_src
from handler_create import Table, table_identity, walk
from handler_index import STRUCT_TYPE, TYPEDEF_STRUCT, declarator_name
from php_src_c.source import QUALIFIERS, matching, parameter_type

HANDLERS = "handlers"
WRITE = re.compile(r"\bhandlers\s*=(?!=)")
STRUCT_HEAD = re.compile(r"\b(typedef\s+)?struct\s*(\w*)\s*\{")
OBJECT_TYPE = "zend_object"
ALIAS = re.compile(r"\s*(\w+)\s*;")


class Disposition:
    """What one write site of the handlers field is: ``kind`` is create, copy, typed or foreign; ``struct`` the object
    struct type the write concerns (None for create and foreign); ``tables`` the tables a typed write names."""

    def __init__(self, kind, definition, struct=None, tables=()):
        self.kind, self.definition, self.struct, self.tables = kind, definition, struct, list(tables)

    def key(self):
        return self.kind, self.definition.source.relative, self.definition.name, self.struct


class Structs:
    """The struct types of a checkout: their members by tag and by typedef name."""

    def __init__(self, program):
        self.program, self.members = program, None

    def read(self):
        found, aliases = collections.defaultdict(list), []
        for source in self.program.sources:
            text = source.text
            for head in STRUCT_HEAD.finditer(text):
                opening = head.end() - 1
                closing = matching(text, opening, "{", "}")
                if closing < 0:
                    continue
                alias = ALIAS.match(text, closing + 1) if head.group(1) else None
                members = [m.strip() for m in split_semicolons(text[opening + 1:closing]) if m.strip()]
                for name in (head.group(2), alias.group(1) if alias else None):
                    if name:
                        found[name].extend(members)
            for tag, alias in TYPEDEF_STRUCT.findall(text):
                aliases.append((tag, alias))
        for tag, alias in aliases:
            if tag in found:
                found[alias] = found[tag]
        return found

    def of(self, name):
        if self.members is None:
            self.members = self.read()
        return self.members.get(name, ())

    def member_type(self, struct, field):
        """The type name of a member of a struct, or None."""
        for member in self.of(struct):
            if declarator_name(member) == field:
                return parameter_type(member)
        return None

    def holds_other_handlers(self, struct):
        """True when the struct declares a ``handlers`` member of a type other than the object handler table: the
        member belongs to something that is not a PHP object."""
        found = self.member_type(struct, HANDLERS)
        return found is not None and found != STRUCT_TYPE


def split_semicolons(body):
    """The members of a struct body: its text split at the semicolons outside nested braces."""
    members, depth, start = [], 0, 0
    for i, char in enumerate(body):
        depth += (char == "{") - (char == "}")
        if char == ";" and depth == 0:
            members.append(body[start:i])
            start = i + 1
    return members


def is_handlers_write(node):
    return (len(node) > 3 and node[0] == "assign" and node[1] == "=" and isinstance(node[2], tuple)
            and node[2][0] == "member" and node[2][2] == HANDLERS)


class Sites:
    """The dispositions of the handler write sites of one checkout."""

    def __init__(self, registered, creation):
        self.registered, self.creation = registered, creation
        self.index, self.program = registered.index, registered.program
        self.structs = Structs(self.program)

    def classify(self):
        """The Disposition of every write site of a handlers field in the function bodies of the checkout."""
        found = []
        for definitions in self.program.functions.values():
            for definition in definitions:
                if not definition.is_macro and WRITE.search(definition.body):
                    found.extend(self.in_function(definition))
        return found

    def in_function(self, definition):
        code = self.index.code(definition)
        if code.failure:
            raise php_src.ExtractionFailure(
                f"{definition.source.relative}: {definition.name}: writes a handlers field in a body no rule reads: "
                f"{code.failure}"
            )
        scope = self.scope(definition, code)
        return [self.site(definition, node, scope) for node in self.writes(code)]

    @staticmethod
    def writes(code):
        for instruction in code.instrs:
            for node in walk(instruction):
                if is_handlers_write(node):
                    yield node

    @staticmethod
    def scope(definition, code):
        """The declared type name of each parameter and local variable of a function."""
        scope = dict(definition.param_types)
        for instruction in code.instrs:
            if instruction[0] == "d":
                words = [w for w in instruction[5] if w.isidentifier() and w not in QUALIFIERS]
                scope[instruction[1]] = words[-1] if words else None
        return scope

    def site(self, definition, node, scope):
        if id(node) in self.creation.executed:
            return Disposition("create", definition)
        holder = node[2][1]
        struct = self.object_struct(holder, scope)
        if struct is None:
            return self.foreign(definition, node, holder, scope)
        source = self.copied_struct(node[3], scope)
        if source is not None:
            return self.copy(definition, struct, source)
        tables = self.named_tables(node[3], definition)
        if not tables:
            raise self.unclassified(definition, "the table written is not a named table or a copy")
        return Disposition("typed", definition, struct, tables)

    def object_struct(self, holder, scope):
        """The struct type whose embedded object a holder expression denotes, or None when it denotes no object."""
        if holder[0] != "member":
            return None
        owner = self.type_of(holder[1], scope)
        return owner if owner and self.structs.member_type(owner, holder[2]) == OBJECT_TYPE else None

    def type_of(self, node, scope):
        kind = node[0]
        if kind == "name":
            return scope.get(node[1])
        if kind == "member":
            owner = self.type_of(node[1], scope)
            return self.structs.member_type(owner, node[2]) if owner else None
        if kind == "cast":
            words = [w for w in node[1] if w.isidentifier() and w not in QUALIFIERS]
            return words[-1] if words else None
        return self.type_of(node[2], scope) if kind == "un" and node[1] in ("*", "&") else None

    def foreign(self, definition, node, holder, scope):
        owner = self.type_of(holder, scope)
        if owner and self.structs.holds_other_handlers(owner):
            return Disposition("foreign", definition)
        raise self.unclassified(definition, "the written holder is neither an object struct nor a foreign struct")

    def copied_struct(self, right, scope):
        """The object struct type whose table a right-hand side reads (``other->std.handlers``), or None."""
        if right[0] == "member" and right[2] == HANDLERS and right[1][0] == "member":
            return self.object_struct(right[1], scope)
        return None

    @staticmethod
    def copy(definition, struct, source):
        if struct != source:
            raise Sites.unclassified(definition, f"copies the table of a {source} object into a {struct} object")
        return Disposition("copy", definition, struct)

    def named_tables(self, node, definition):
        """The tables a right-hand side names: ``&table``, either branch of a conditional, or a cast of those."""
        kind = node[0]
        if kind == "un" and node[1] == "&" and node[2][0] == "name":
            region = self.index.table_region(node[2][1], definition.source)
            declarations = self.registered.world.declarations.get(region) if region else None
            return [Table(region, table_identity(declarations))] if declarations else []
        if kind == "cond":
            return self.named_tables(node[2], definition) + self.named_tables(node[3], definition)
        return self.named_tables(node[2], definition) if kind == "cast" else []

    @staticmethod
    def unclassified(definition, reason):
        return php_src.ExtractionFailure(
            f"{definition.source.relative}: {definition.name}: unclassified write of a handlers field: {reason}"
        )


def typed_tables(dispositions):
    """The tables of the typed writes, by the object struct type they are written to."""
    tables = collections.defaultdict(list)
    for disposition in dispositions:
        if disposition.kind == "typed":
            tables[disposition.struct].extend(disposition.tables)
    return {struct: list(dict.fromkeys(found)) for struct, found in tables.items()}
