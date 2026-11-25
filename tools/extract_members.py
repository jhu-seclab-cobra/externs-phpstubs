#!/usr/bin/env python3
"""Give the generated set the typed property and typed class constant entries php-src declares (design-extraction.md,
extract_members.py).

Reads every class-like body of the php-src stubs: each property and each class constant with a declared type becomes
one property or class constant entry holding that type, its class resolved by PHP's name resolution rules, and for a
property its visibility and staticness. A declaration without a type states no check for a redeclaration and gets no
entry. An entry lives in the generated document of its php-src extension, moved there when another document holds
it, and each declaration no models document declares is added to the generated document declaring its class. A
generated entry php-src declares has its signature rewritten, every other line untouched. A second run over its own
output changes nothing.
"""

import argparse
import re
import sys
from pathlib import Path

import extract_signatures
import php_src

TOOL = "tools/extract_members.py"

MODIFIERS = r"(?:public|protected|private|static|readonly|var|abstract|final)(?:\(set\))?"
MODIFIER_PREFIX = re.compile(rf"^(?:{MODIFIERS}\s+)*")
VISIBILITY = re.compile(r"\b(public|protected|private)\b(?!\(set\))")
STATIC = re.compile(r"\bstatic\b")
FUNCTION = re.compile(r"\bfunction\b")
CONSTANT_HEAD = re.compile(rf"^((?:{MODIFIERS}\s+)*)const\s+(.*)$", re.S)
# What ends the head of a property or constant: its default value, the body of its hooks, or its terminator.
HEAD_END = re.compile(r"[={;]")


class Member:
    """One typed property or class constant: its kind, spelled subject, declared type, and the stub that declares it."""

    def __init__(self, kind, subject, type_, source, visibility=None, static=False):
        self.kind, self.subject, self.type, self.source = kind, subject, type_, source
        self.visibility, self.static = visibility, static

    def key(self):
        return php_src.identity(self.kind, self.subject)

    def same_declaration(self, other):
        return (self.type, self.visibility, self.static) == (other.type, other.visibility, other.static)

    def render(self):
        lines = ["- subject:", f"    {self.kind}: {self.subject}", "  signature:", f"    type: {extract_signatures.scalar(self.type)}"]
        if self.kind == "property":
            lines.append(f"    visibility: {self.visibility}")
            lines += ["    static: true"] * self.static
        return "\n".join(lines) + "\n"


def statements(text, body):
    """The (offset, text) of each statement directly in a class body: up to its `;`, or to the `}` closing a block."""
    start, end = body
    depth, begin, i = 0, start + 1, start + 1
    while i < end:
        char = text[i]
        if char in "'\"":
            i = php_src.skip_string(text, i)
            continue
        depth += (char in php_src.OPENERS) - (char in php_src.CLOSERS)
        if depth == 0 and char in ";}":
            yield begin, text[begin : i + 1]
            begin = i + 1
        i += 1


def head_of(statement):
    """The statement up to its default value, hook block or terminator."""
    end = HEAD_END.search(statement)
    return statement[: end.start()] if end else statement


def read_statement(stub, owner, offset, statement):
    """The Member a class body statement declares, or None for any other statement or an untyped declaration."""
    head = head_of(statement).strip()
    constant = CONSTANT_HEAD.match(head)
    if constant:
        words = constant.group(2).split()
        if len(words) < 2:
            return None
        spelled = "".join(words[:-1])
        return Member("class_constant", f"{owner}::{words[-1]}", extract_signatures.declared_type(spelled, stub, offset), stub.source)
    if "$" not in head or FUNCTION.search(head):
        return None
    name = re.search(r"\$(\w+)$", head)
    if name is None:
        raise php_src.ExtractionFailure(f"{stub.source}: unreadable property declaration {head!r}")
    modifiers = MODIFIER_PREFIX.match(head).group(0)
    spelled = head[len(modifiers) : name.start()].strip()
    if not spelled:
        return None
    visibility = VISIBILITY.search(modifiers)
    return Member(
        "property",
        f"{owner}::${name.group(1)}",
        extract_signatures.declared_type(spelled, stub, offset),
        stub.source,
        visibility.group(1) if visibility else "public",
        bool(STATIC.search(modifiers)),
    )


def read_stub(stub):
    """Yield the Member of every typed property and class constant one stub declares."""
    for start, end, owner in extract_signatures.class_bodies(stub):
        for offset, statement in statements(stub.text, (start, end)):
            member = read_statement(stub, owner, offset, statement)
            if member is not None:
                yield member


def read_php_src(root):
    """Return the (kind, folded subject) → Member map; every declaration of one subject must agree."""
    members = {}
    for stub in php_src.stubs(root):
        for member in read_stub(stub):
            known = members.setdefault(member.key(), member)
            if not known.same_declaration(member):
                raise php_src.ExtractionFailure(
                    f"{member.subject}: {known.source} and {member.source} declare different types"
                )
    return members


def target_document(member, class_documents):
    """The generated document declaring the class of a member."""
    owner = member.subject.split("::")[0].lower()
    if ("class", owner) not in class_documents:
        raise php_src.ExtractionFailure(f"{member.subject}: no generated document declares class {owner}")
    return class_documents[("class", owner)]


def relocate(models, members):
    """Move each generated member entry php-src declares to the document of its php-src extension."""
    extensions = {key: php_src.extension_of(member.source) for key, member in members.items()}
    return php_src.relocate(models, extensions, TOOL)


def add_missing(models, members):
    """Add every php-src member no models document declares; return the number added."""
    known = php_src.declared(php_src.all_documents(models))
    class_documents = php_src.declared(php_src.generated_documents(models))
    additions = {}
    for key in sorted(members):
        if key not in known:
            additions.setdefault(target_document(members[key], class_documents), []).append(members[key].render())
    for document, rendered in additions.items():
        php_src.append(document, rendered, TOOL)
    return sum(len(rendered) for rendered in additions.values())


def rewrite(models, members):
    """Rewrite the signature of each generated member entry php-src declares."""

    def transform(entry):
        member = members.get(entry.key())
        if member is None:
            return entry.text
        return member.render() + entry.without_signature()

    return php_src.rewrite(models, transform)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--php-src", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    try:
        members = read_php_src(args.php_src)
        moved = relocate(args.models, members)
        added = add_missing(args.models, members)
        changed = rewrite(args.models, members)
    except php_src.ExtractionFailure as failure:
        print(f"{TOOL}: {failure}", file=sys.stderr)
        sys.exit(1)
    print(
        f"{TOOL}: {len(members)} php-src members, {moved} entries moved, {added} entries added, "
        f"{changed} documents rewritten"
    )


if __name__ == "__main__":
    main()
