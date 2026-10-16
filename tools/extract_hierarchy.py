#!/usr/bin/env python3
"""Give the generated class entries their php-src hierarchy (design-extraction.md, extract_hierarchy.py).

Reads every class-like declaration of the php-src stubs, resolves its
``extends`` and ``implements`` names by PHP's name resolution rules, and
rewrites the signature of every generated class entry php-src declares:
classifier, parent, and interfaces from php-src, every other line untouched.
Each such entry lives in the generated document of its php-src extension,
moved there when another document holds it, and a php-src declaration no
models document declares is added there. A second run over its own output changes nothing.
"""

import argparse
import re
import sys
from pathlib import Path

import php_src

TOOL = "tools/extract_hierarchy.py"

DECLARATION = re.compile(r"\b(?:(?:final|abstract|readonly)\s+)*(class|interface|enum|trait)\s+(\w+)([^{;]*)\{")
HEADER = re.compile(
    r"^(?:\s*:\s*(?P<backing>\w+))?(?:\s+extends\s+(?P<extends>[\w\\,\s]+?))?"
    r"(?:\s+implements\s+(?P<implements>[\w\\,\s]+?))?\s*$"
)
# The interfaces the engine appends to every enum, and to a backed enum (Zend/zend_enum.c, zend_enum_add_interfaces).
ENUM_INTERFACES = ["unitenum"]
BACKED_ENUM_INTERFACES = ["unitenum", "backedenum"]


class Declaration:
    """One class-like declaration: classifier, folded parent, folded interfaces, and its stub."""

    def __init__(self, classifier, parent, interfaces, source):
        self.classifier, self.parent, self.interfaces, self.source = classifier, parent, interfaces, source

    def key(self):
        return self.classifier, self.parent, tuple(self.interfaces)

    def render_signature(self):
        lines = ["  signature:", f"    classifier: {self.classifier}"]
        if self.parent:
            lines.append(f"    parent: {self.parent}")
        if self.interfaces:
            lines.append(f"    interfaces: [{', '.join(self.interfaces)}]")
        return "\n".join(lines) + "\n"

    def render(self, name):
        return f"- subject:\n    class: {name}\n" + self.render_signature()


def names(text, stub, offset):
    return [stub.resolve(n.strip(), offset).lower() for n in (text or "").split(",") if n.strip()]


def declaration_of(match, stub):
    """Build the Declaration of one matched class-like header.

    An interface's extends names are interfaces; an enum implements the engine's enum interfaces after its own.
    """
    classifier, short, header = match.groups()
    parsed = HEADER.match(header)
    if not parsed:
        raise php_src.ExtractionFailure(f"{stub.source}: unreadable declaration header of {short}: {header.strip()!r}")
    extends = names(parsed.group("extends"), stub, match.start())
    implements = names(parsed.group("implements"), stub, match.start())
    if classifier == "interface":
        return Declaration(classifier, None, extends + implements, stub.source)
    if classifier == "enum":
        implicit = BACKED_ENUM_INTERFACES if parsed.group("backing") else ENUM_INTERFACES
        return Declaration(classifier, None, implements + implicit, stub.source)
    if len(extends) > 1:
        raise php_src.ExtractionFailure(f"{stub.source}: {classifier} {short} extends more than one class")
    return Declaration(classifier, extends[0] if extends else None, implements, stub.source)


def read_php_src(root):
    """Return the folded name → Declaration map of every stub."""
    declarations = {}
    for stub in php_src.stubs(root):
        for match in DECLARATION.finditer(stub.text):
            declaration = declaration_of(match, stub)
            name = php_src.resolve(match.group(2), stub.namespace_at(match.start()), {}).lower()
            known = declarations.setdefault(name, declaration)
            if known.key() != declaration.key():
                raise php_src.ExtractionFailure(f"{name}: {known.source} and {declaration.source} declare different hierarchies")
    return declarations


def relocate(models, declarations):
    """Move each generated class entry php-src declares to the document of its php-src extension."""
    extensions = {("class", name): php_src.extension_of(d.source) for name, d in declarations.items()}
    return php_src.relocate(models, extensions, TOOL)


def add_missing(models, declarations):
    """Add each php-src declaration no models document declares to the document of its extension."""
    known = php_src.declared(php_src.all_documents(models))
    additions = {}
    for name in sorted(declarations):
        if ("class", name) in known:
            continue
        document = php_src.placement(models, php_src.extension_of(declarations[name].source))
        additions.setdefault(document, []).append(declarations[name].render(name))
    for document, rendered in additions.items():
        php_src.append(document, rendered, TOOL)
    return sum(len(rendered) for rendered in additions.values())


def rewrite(models, declarations):
    """Rewrite the signature of each generated class entry php-src declares."""

    def transform(entry):
        declaration = declarations.get(entry.subject.lower()) if entry.kind == "class" else None
        return entry.with_signature(declaration.render_signature()) if declaration else entry.text

    return php_src.rewrite(models, transform)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--php-src", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    try:
        declarations = read_php_src(args.php_src)
        moved = relocate(args.models, declarations)
        added = add_missing(args.models, declarations)
        changed = rewrite(args.models, declarations)
    except php_src.ExtractionFailure as failure:
        print(f"{TOOL}: {failure}", file=sys.stderr)
        sys.exit(1)
    print(
        f"{TOOL}: {len(declarations)} php-src declarations, {moved} classes moved, {added} classes added, "
        f"{changed} documents rewritten"
    )


if __name__ == "__main__":
    main()
