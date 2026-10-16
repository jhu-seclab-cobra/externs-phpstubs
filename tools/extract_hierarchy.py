#!/usr/bin/env python3
"""Give the generated class entries their php-src hierarchy (design.md, Class Hierarchy Extraction).

Reads every ``*.stub.php`` of one php-src checkout outside test directories,
resolves each class-like declaration's ``extends`` and ``implements`` names
by PHP's name resolution rules, and rewrites the class entries of the
generated documents under the models directory in place: classifier,
parent, and interfaces from php-src, every other line untouched. A parent or
interface no models document declares is appended to ``core.yaml`` until
every named class is declared. A second run over its own output changes
nothing.
"""

import argparse
import re
import sys
from pathlib import Path

SCRIPT = "tools/extract_hierarchy.py"
CLASS_DOCUMENT = "core.yaml"
HAND_DECLARED = ("language", "manual")
SKIPPED_DOCUMENTS = ("provenance.yaml",)
SKIPPED_SOURCE_PARTS = ("tests", "zend_test", "dl_test")

NAMESPACE = re.compile(r"^namespace(?:\s+([\w\\]+))?\s*[;{]", re.M)
USE = re.compile(r"^\s*use\s+\\?([\w\\]+)(?:\s+as\s+(\w+))?\s*;", re.M)
DECLARATION = re.compile(
    r"^[ \t]*(?:(?:final|abstract|readonly)\s+)*(class|interface|enum|trait)\s+(\w+)([^{;]*)\{", re.M
)
HEADER = re.compile(r"^(?:\s*:\s*\w+)?(?:\s+extends\s+([\w\\,\s]+?))?(?:\s+implements\s+([\w\\,\s]+?))?\s*$")
CLASS_ENTRY = re.compile(
    r"^- subject:\n    class: (\S+)\n  signature:\n    classifier: \w+\n(?:    parent: \S+\n)?(?:    interfaces: \[[^\]\n]*\]\n)?",
    re.M,
)
DECLARED_CLASS = re.compile(r"^    class: (\S+)$", re.M)


class Declaration:
    """One class-like declaration: classifier, folded parent, folded interfaces."""

    def __init__(self, classifier, parent, interfaces, source):
        self.classifier = classifier
        self.parent = parent
        self.interfaces = interfaces
        self.source = source

    def key(self):
        return self.classifier, self.parent, tuple(self.interfaces)

    def render(self, name):
        lines = ["- subject:", f"    class: {name}", "  signature:", f"    classifier: {self.classifier}"]
        if self.parent:
            lines.append(f"    parent: {self.parent}")
        if self.interfaces:
            lines.append(f"    interfaces: [{', '.join(self.interfaces)}]")
        return "\n".join(lines) + "\n"


def fail(message):
    print(f"{SCRIPT}: {message}", file=sys.stderr)
    sys.exit(1)


def resolve(name, namespace, imports):
    """Resolve a class name as PHP does: fully qualified, imported, or relative to the namespace."""
    if name.startswith("\\"):
        return name[1:].lower()
    head, _, rest = name.partition("\\")
    if head.lower() in imports:
        target = imports[head.lower()]
        return (target + ("\\" + rest if rest else "")).lower()
    return ((namespace + "\\" if namespace else "") + name).lower()


def names(text, namespace, imports):
    return [resolve(n.strip(), namespace, imports) for n in (text or "").split(",") if n.strip()]


def declaration_of(match, namespace, imports, source):
    """Build the Declaration of one matched class-like header; an interface's extends names are interfaces."""
    classifier, short, header = match.groups()
    parsed = HEADER.match(header)
    if not parsed:
        fail(f"{source}: unreadable declaration header of {short}: {header.strip()!r}")
    extends, implements = names(parsed.group(1), namespace, imports), names(parsed.group(2), namespace, imports)
    if classifier == "interface":
        return Declaration(classifier, None, extends + implements, source)
    if len(extends) > 1:
        fail(f"{source}: {classifier} {short} extends more than one class")
    return Declaration(classifier, extends[0] if extends else None, implements, source)


def read_php_src(root):
    """Return the folded name → Declaration map of every stub outside test directories."""
    declarations = {}
    for path in sorted(root.rglob("*.stub.php")):
        source = path.relative_to(root)
        if any(part in SKIPPED_SOURCE_PARTS for part in source.parts):
            continue
        text = path.read_text(encoding="utf-8")
        spaces = [(m.start(), m.group(1) or "") for m in NAMESPACE.finditer(text)]
        imports = {(m.group(2) or m.group(1).rsplit("\\", 1)[-1]).lower(): m.group(1) for m in USE.finditer(text)}
        for match in DECLARATION.finditer(text):
            namespace = next((ns for start, ns in reversed(spaces) if start < match.start()), "")
            declaration = declaration_of(match, namespace, imports, source)
            name = resolve(match.group(2), namespace, {})
            known = declarations.setdefault(name, declaration)
            if known.key() != declaration.key():
                fail(f"{name}: {known.source} and {declaration.source} declare different hierarchies")
    return declarations


def generated_documents(models):
    for path in sorted(models.rglob("*.yaml")):
        relative = path.relative_to(models)
        if relative.parts[0] in HAND_DECLARED or path.name in SKIPPED_DOCUMENTS:
            continue
        yield path


def declared_classes(models):
    return {name for path in sorted(models.rglob("*.yaml")) for name in DECLARED_CLASS.findall(path.read_text(encoding="utf-8"))}


def rewrite(models, declarations):
    """Rewrite each generated class entry php-src declares; return the number of documents changed."""
    changed = 0
    for path in generated_documents(models):
        text = path.read_text(encoding="utf-8")

        def entry(match):
            declaration = declarations.get(match.group(1))
            return declaration.render(match.group(1)) if declaration else match.group(0)

        updated = CLASS_ENTRY.sub(entry, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def close(models, declarations):
    """Append to core.yaml every parent or interface no models document declares, transitively."""
    declared = declared_classes(models)
    pending = sorted(
        {n for name in declared if name in declarations for n in [declarations[name].parent, *declarations[name].interfaces] if n}
        - declared
    )
    added = []
    while pending:
        name = pending.pop(0)
        if name in declared:
            continue
        declaration = declarations.get(name)
        if declaration is None:
            fail(f"{name} is named as a parent or interface but php-src declares no {name}")
        declared.add(name)
        added.append(name)
        pending.extend(sorted(n for n in [declaration.parent, *declaration.interfaces] if n and n not in declared))
    if added:
        document = models / CLASS_DOCUMENT
        text = document.read_text(encoding="utf-8")
        document.write_text(text + "".join(declarations[name].render(name) for name in added), encoding="utf-8")
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--php-src", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    declarations = read_php_src(args.php_src)
    if not declarations:
        fail(f"no stub declarations under {args.php_src}")
    added = close(args.models, declarations)
    changed = rewrite(args.models, declarations)
    print(f"{SCRIPT}: {len(declarations)} php-src declarations, {len(added)} classes added, {changed} documents rewritten")


if __name__ == "__main__":
    main()
