"""Class registrations, builtin entries and linkage of a php-src checkout (design-extraction-handlers.md)."""

import collections
import re

import php_src
from php_src_c.definitions import Definition, definitions_of
from php_src_c.macros import Preprocessor
from php_src_c.source import CALL, SOURCE_SUFFIXES, STRING_PLACEHOLDER, Source, matching, matching_brace, split_arguments

FUNCTION_TABLE = re.compile(r"\bzend_function_entry\s+(\w+)\s*\[\s*\]\s*=\s*\{")
FRAMELESS_TABLE = re.compile(r"\bzend_frameless_function_info\s+(\w+)\s*\[\s*\]\s*=\s*\{")
REGISTERED_CLASS = re.compile(r"\b(\w+)\s*=\s*(register_class_\w+)\s*\(")
# Function entry macros of the arginfo tables: the PHP name and the handler (zend_API.h).
ENTRY_MACROS = {"ZEND_FE", "ZEND_ME", "ZEND_RAW_FENTRY"}
METHOD_MACRO = "ZEND_ME"
ENTRY_END = "ZEND_FE_END"
# The calls that register a class: its name, then its kind, parent and flags (zend_API.h).
NAME_CALLS = {"INIT_CLASS_ENTRY", "INIT_NS_CLASS_ENTRY"}
REGISTRATION_CALLS = {
    "zend_register_internal_class_with_flags", "zend_register_internal_class_ex", "zend_register_internal_interface",
    "zend_register_internal_enum",
}


class Registration:
    """One class registration function of an arginfo file: the class it registers and how.

    ``kind`` is class, interface, enum or trait; ``flags`` the ZEND_ACC_ names the registration call passes;
    ``parent`` the parent class entry expression, or None."""

    def __init__(self, function, name, kind, flags, parent, source):
        self.function, self.name, self.kind, self.flags, self.parent, self.source = function, name, kind, flags, parent, source


class Program:
    """Every definition of one php-src checkout, with C linkage, class entries, and builtin entries."""

    def __init__(self, root, provenance=False):
        self.strings, self.sources, self.unowned = [], [], set()
        self.functions = collections.defaultdict(list)
        for path in php_src.source_files(root, SOURCE_SUFFIXES):
            source = Source(path, self.strings, provenance)
            source.relative, source.is_header = path.relative_to(root), path.suffix == ".h"
            self.sources.append(source)
        self.preprocessor = Preprocessor(self.sources, self.strings)
        for source in self.sources:
            self.preprocessor.expand_definitions(source)
            self.load(source)
        self.class_names = self.registered_class_names()
        self.class_entries = {
            variable: self.class_names[register]
            for source in self.sources
            for variable, register in REGISTERED_CLASS.findall(source.text)
            if register in self.class_names
        }
        self.registrations = self.registered_classes()

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

    def registered_classes(self):
        """Folded PHP class name → the Registration of its register_class function; two functions registering the
        same name fail the run."""
        found = {}
        for function in sorted(self.functions):
            if not function.startswith("register_class_"):
                continue
            for definition in self.functions[function]:
                registration = self.registration(definition)
                if registration is None:
                    continue
                known = found.setdefault(registration.name.lower(), registration)
                if known is not registration:
                    raise php_src.ExtractionFailure(
                        f"{registration.name.lower()}: registered by {known.function} ({known.source}) "
                        f"and {registration.function} ({registration.source})"
                    )
        return found

    def registration(self, definition):
        name, kind, flags, parent = None, "class", frozenset(), None
        for match in CALL.finditer(definition.body):
            callee = match.group(1)
            if callee not in REGISTRATION_CALLS and callee not in NAME_CALLS:
                continue
            args = split_arguments(definition.body[match.end():matching(definition.body, match.end() - 1)])
            if callee == "INIT_CLASS_ENTRY":
                name = self.string(args[1])
            elif callee == "INIT_NS_CLASS_ENTRY":
                name = self.string(args[1]) + "\\" + self.string(args[2])
            elif callee == "zend_register_internal_enum":
                name, kind = self.string(args[0]), "enum"
            elif callee == "zend_register_internal_interface":
                kind = "interface"
            else:
                parent = None if args[1] in ("NULL", "nullptr") else args[1]
                flags = frozenset(f.strip() for f in args[2].split("|")) - {"0"} if len(args) > 2 else frozenset()
                kind = "trait" if "ZEND_ACC_TRAIT" in flags else "class"
        if name is None:
            return None
        return Registration(definition.name, name, kind, flags, parent, definition.source.relative)

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
