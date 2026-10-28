#!/usr/bin/env python3
"""Give the generated class entries their php-src hierarchy (design-extraction.md, extract_hierarchy.py).

Reads every class-like declaration of the php-src stubs, resolves its
``extends`` and ``implements`` names by PHP's name resolution rules, reads the
registered flags and the effective handler tables of the registered classes,
and rewrites the signature of every generated class entry php-src declares:
classifier, parent, interfaces, final-class status and handlers from php-src,
every other line untouched. Each such entry lives in the generated document of
its php-src extension, moved there when another document holds it, and a
php-src declaration no models document declares is added there. An entry php-src
does not declare keeps its bytes. A second run over its own output changes nothing.
"""

import argparse
import re
import sys
from pathlib import Path

import php_src
from handler_facts import read_handler_tables
from handler_render import render_handlers
from php_src_c import Program

TOOL = "tools/extract_hierarchy.py"
# The signature fields this producer writes; every other field of an entry stays as it is.
OWNED_FIELDS = ("classifier", "parent", "interfaces", "isFinal", "handlers")

DECLARATION = re.compile(r"\b((?:(?:final|abstract|readonly)\s+)*)(class|interface|enum|trait)\s+(\w+)([^{;]*)\{")
STRING_METHOD = re.compile(r"\bfunction\s+__toString\b", re.I)
FINAL_FLAG = "ZEND_ACC_FINAL"
HEADER = re.compile(
    r"^(?:\s*:\s*(?P<backing>\w+))?(?:\s+extends\s+(?P<extends>[\w\\,\s]+?))?"
    r"(?:\s+implements\s+(?P<implements>[\w\\,\s]+?))?\s*$"
)
# The interfaces the engine appends to every enum, and to a backed enum (Zend/zend_enum.c, zend_enum_add_interfaces).
ENUM_INTERFACES = ["unitenum"]
BACKED_ENUM_INTERFACES = ["unitenum", "backedenum"]


class Declaration:
    """One class-like declaration: classifier, folded parent, folded interfaces, its stub, whether the stub declares
    it final, and whether its body declares a ``__toString`` method."""

    def __init__(self, classifier, parent, interfaces, source, final=False, to_string=False):
        self.classifier, self.parent, self.interfaces, self.source = classifier, parent, interfaces, source
        self.final, self.to_string = final, to_string

    def key(self):
        return self.classifier, self.parent, tuple(self.interfaces), self.final

    def render_signature(self, is_final=None, handlers=()):
        """The signature lines: the declaration fields, the registered final-class status when established, and the
        handler tables when the class has any."""
        lines = ["  signature:", f"    classifier: {self.classifier}"]
        if self.parent:
            lines.append(f"    parent: {self.parent}")
        if self.interfaces:
            lines.append(f"    interfaces: [{', '.join(self.interfaces)}]")
        if is_final is not None:
            lines.append(f"    isFinal: {'true' if is_final else 'false'}")
        return "\n".join(lines) + "\n" + render_handlers(handlers)

    def render(self, name, is_final=None, handlers=()):
        return f"- subject:\n    class: {name}\n" + self.render_signature(is_final, handlers)


def names(text, stub, offset):
    return [stub.resolve(n.strip(), offset).lower() for n in (text or "").split(",") if n.strip()]


def declaration_of(match, stub):
    """Build the Declaration of one matched class-like header.

    An interface's extends names are interfaces; an enum implements the engine's enum interfaces after its own.
    """
    modifiers, classifier, short, header = match.groups()
    final = "final" in modifiers.split()
    parsed = HEADER.match(header)
    if not parsed:
        raise php_src.ExtractionFailure(f"{stub.source}: unreadable declaration header of {short}: {header.strip()!r}")
    extends = names(parsed.group("extends"), stub, match.start())
    implements = names(parsed.group("implements"), stub, match.start())
    opening = match.end() - 1
    to_string = bool(STRING_METHOD.search(stub.text, opening, php_src.matching(stub.text, opening, stub.source)))
    if classifier == "interface":
        return Declaration(classifier, None, extends + implements, stub.source, final, to_string)
    if classifier == "enum":
        implicit = BACKED_ENUM_INTERFACES if parsed.group("backing") else ENUM_INTERFACES
        return Declaration(classifier, None, implements + implicit, stub.source, final, to_string)
    if len(extends) > 1:
        raise php_src.ExtractionFailure(f"{stub.source}: {classifier} {short} extends more than one class")
    return Declaration(classifier, extends[0] if extends else None, implements, stub.source, final, to_string)


def read_php_src(root):
    """Return the folded name → Declaration map of every stub."""
    declarations = {}
    for stub in php_src.stubs(root):
        for match in DECLARATION.finditer(stub.text):
            declaration = declaration_of(match, stub)
            name = php_src.resolve(match.group(3), stub.namespace_at(match.start()), {}).lower()
            known = declarations.setdefault(name, declaration)
            if known.key() != declaration.key():
                raise php_src.ExtractionFailure(f"{name}: {known.source} and {declaration.source} declare different hierarchies")
    return declarations


def registered_finality(program, declarations):
    """The final-class status of each declared class php-src registers: whether its registration passes the FINAL
    flag. A class no registration names has none. A stub that declares a class final while its registration does not
    is a conflict."""
    finals = {}
    for name, registration in program.registrations.items():
        declaration = declarations.get(name)
        if declaration is None:
            continue
        flagged = FINAL_FLAG in registration.flags
        if declaration.final and not flagged:
            raise php_src.ExtractionFailure(
                f"{name}: {declaration.source} declares it final, {registration.source} registers it without {FINAL_FLAG}"
            )
        finals[name] = flagged
    return finals


class Generated:
    """What php-src establishes for the class entries: the declarations, the registered final-class status and the
    handler tables of the registered classes."""

    def __init__(self, declarations, finals, handlers):
        self.declarations, self.finals, self.handlers = declarations, finals, handlers

    def signature(self, name):
        return self.declarations[name].render_signature(self.finals.get(name), self.handlers.get(name, ()))

    def entry(self, name):
        return self.declarations[name].render(name, self.finals.get(name), self.handlers.get(name, ()))


def relocate(models, declarations):
    """Move each generated class entry php-src declares to the document of its php-src extension."""
    extensions = {("class", name): php_src.extension_of(d.source) for name, d in declarations.items()}
    return php_src.relocate(models, extensions, TOOL)


def add_missing(models, generated):
    """Add each php-src declaration no models document declares to the document of its extension."""
    known = php_src.declared(php_src.all_documents(models))
    additions = {}
    for name in sorted(generated.declarations):
        if ("class", name) in known:
            continue
        document = php_src.placement(models, php_src.extension_of(generated.declarations[name].source))
        additions.setdefault(document, []).append(generated.entry(name))
    for document, rendered in additions.items():
        php_src.append(document, rendered, TOOL)
    return sum(len(rendered) for rendered in additions.values())


def rewrite(models, generated):
    """Rewrite the owned fields of the signature of each generated class entry php-src declares."""

    def transform(entry):
        name = entry.subject.lower()
        if entry.kind != "class" or name not in generated.declarations:
            return entry.text
        return entry.with_signature(generated.signature(name), OWNED_FIELDS)

    return php_src.rewrite(models, transform)


def generate(root):
    """The Generated facts of one php-src checkout."""
    declarations = read_php_src(root)
    program = Program(root, provenance=True)
    handlers, _ = read_handler_tables(program, declarations)
    return Generated(declarations, registered_finality(program, declarations), handlers)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--php-src", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    try:
        generated = generate(args.php_src)
        moved = relocate(args.models, generated.declarations)
        added = add_missing(args.models, generated)
        changed = rewrite(args.models, generated)
    except php_src.ExtractionFailure as failure:
        print(f"{TOOL}: {failure}", file=sys.stderr)
        sys.exit(1)
    print(
        f"{TOOL}: {len(generated.declarations)} php-src declarations, {len(generated.handlers)} classes with handler "
        f"tables, {moved} classes moved, {added} classes added, {changed} documents rewritten"
    )


if __name__ == "__main__":
    main()
