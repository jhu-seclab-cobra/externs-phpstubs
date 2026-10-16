"""Shared reading, placement, and writing of the php-src producers (design-extraction.md, php_src).

Reads one php-src checkout (source files, stub text with its namespace scope)
and the models directory (generated documents, entry spans), places a new
entry in the document of its extension, and rewrites entry spans in place.
Imports no tool.
"""

import re
from pathlib import Path

HAND_DECLARED = ("language", "manual")
SET_DOCUMENTS = ("provenance.yaml",)
SKIPPED_SOURCE_PARTS = ("tests", "zend_test", "dl_test", "skeleton")
# The extension a php-src directory outside ext/ registers its declarations under (PHP reflection).
EXTENSION_OF_DIRECTORY = {"Zend": "core", "main": "standard", "sapi": "standard"}
# A document split into numbered parts names its extension without the part number.
SPLIT_SUFFIX = re.compile(r"_\d+$")
GENERATED_HEADER = "# Generated from php-src stubs by {tool}.\n# Do not hand-edit; corrections belong in a higher configuration layer.\n"

ENTRY_START = re.compile(r"^- subject:\n    (\w+): (\S+)\n", re.M)
SIGNATURE_BLOCK = re.compile(r"^  signature:\n(?:    .*\n)*", re.M)
NAMESPACE = re.compile(r"\bnamespace(?:\s+([\w\\]+))?\s*[;{]")
USE = re.compile(r"^\s*use\s+\\?([\w\\]+)(?:\s+as\s+(\w+))?\s*;", re.M)
OPENERS, CLOSERS = "([{", ")]}"


class ExtractionFailure(Exception):
    """A php-src or models input no rule reads; the tool reports it and exits with status 1."""


class Entry:
    """One entry span of a document: its start offset, subject kind, subject as spelled, and its text."""

    def __init__(self, start, header, text):
        self.start, self.kind, self.subject, self.text = start, header.group(1), header.group(2), text
        self.header_length = len(header.group(0))

    def key(self):
        return self.kind, self.subject.lower()

    def with_signature(self, block):
        """The entry text with its signature block replaced by block, every other line kept."""
        return SIGNATURE_BLOCK.sub(lambda _: block, self.text, count=1)

    def without_signature(self):
        """The entry's sections after the subject lines, its signature block removed."""
        return SIGNATURE_BLOCK.sub("", self.text[self.header_length :], count=1)


class StubText:
    """One stub file with comments blanked (offsets kept), its namespaces, and its imports."""

    def __init__(self, path, root):
        self.source = path.relative_to(root)
        self.raw = path.read_text(encoding="utf-8")
        self.text = strip_comments(self.raw, self.source)
        self.spaces = [(m.start(), m.group(1) or "") for m in NAMESPACE.finditer(self.text)]
        self.imports = {(m.group(2) or m.group(1).rsplit("\\", 1)[-1]).lower(): m.group(1) for m in USE.finditer(self.text)}

    def namespace_at(self, offset):
        return next((ns for start, ns in reversed(self.spaces) if start < offset), "")

    def resolve(self, name, offset):
        return resolve(name, self.namespace_at(offset), self.imports)


def source_files(root, suffixes):
    """Every file of the checkout with one of the suffixes, sorted, outside the skipped directories."""
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.name.endswith(suffixes)
        and path.is_file()
        and not any(part in SKIPPED_SOURCE_PARTS for part in path.relative_to(root).parts)
    ]


def stubs(root):
    """The StubText of every stub of the checkout."""
    found = [StubText(path, root) for path in source_files(root, (".stub.php",))]
    if not found:
        raise ExtractionFailure(f"no stub declarations under {root}")
    return found


def resolve(name, namespace, imports):
    """Resolve a class name as PHP does, keeping its spelling: fully qualified, imported, or namespace-relative."""
    if name.startswith("\\"):
        return name[1:]
    head, _, rest = name.partition("\\")
    if head.lower() in imports:
        return imports[head.lower()] + ("\\" + rest if rest else "")
    return (namespace + "\\" if namespace else "") + name


def extension_of(source):
    """The PHP extension of a php-src file: ext/<dir>, else the extension of its top directory."""
    parts = Path(source).parts
    if parts[0] == "ext":
        return parts[1]
    if parts[0] not in EXTENSION_OF_DIRECTORY:
        raise ExtractionFailure(f"{source}: no extension for directory {parts[0]}")
    return EXTENSION_OF_DIRECTORY[parts[0]]


def generated_documents(models):
    """Every models document except the hand-declared directories and the set documents."""
    return [
        path
        for path in sorted(models.rglob("*.yaml"))
        if path.relative_to(models).parts[0] not in HAND_DECLARED and path.name not in SET_DOCUMENTS
    ]


def document_extension(path):
    """The extension a document's placement encodes: its file name without the split suffix."""
    return SPLIT_SUFFIX.sub("", path.stem)


def placement(models, extension):
    """The document a new entry of extension joins: the last generated document named for it, else a new one."""
    named = [path for path in generated_documents(models) if document_extension(path) == extension]
    return named[-1] if named else models / f"{extension}.yaml"


def relocate(models, extensions, tool):
    """Move each generated entry to placement of the extension extensions maps its key to; return the number moved.

    A document left without an entry is removed.
    """
    moving = {}
    for path in generated_documents(models):
        text = path.read_text(encoding="utf-8")
        spans = entries(text)
        home = document_extension(path)
        targets = [(entry, extensions.get(entry.key(), home)) for entry in spans]
        stays = [entry for entry, extension in targets if extension == home]
        if len(stays) == len(spans):
            continue
        for entry, extension in targets:
            if extension != home:
                moving.setdefault(extension, []).append(entry.text)
        if stays:
            path.write_text(text[: spans[0].start] + "".join(entry.text for entry in stays), encoding="utf-8")
        else:
            path.unlink()
    for extension in sorted(moving):
        append(placement(models, extension), moving[extension], tool)
    return sum(len(moved) for moved in moving.values())


def append(document, entries, tool):
    """Append rendered entries to document, opening a new one with the generated header naming tool."""
    text = document.read_text(encoding="utf-8") if document.exists() else GENERATED_HEADER.format(tool=tool)
    document.write_text(text + "".join(entries), encoding="utf-8")


def entries(text):
    """The entry spans of one document, from one `- subject:` line to the next."""
    starts = list(ENTRY_START.finditer(text))
    ends = [m.start() for m in starts[1:]] + [len(text)]
    return [Entry(m.start(), m, text[m.start() : end]) for m, end in zip(starts, ends)]


def declared(documents):
    """The (kind, folded subject) → document map of every entry the given documents declare."""
    found = {}
    for path in documents:
        for entry in entries(path.read_text(encoding="utf-8")):
            found.setdefault(entry.key(), path)
    return found


def all_documents(models):
    """Every models document except the set documents."""
    return [path for path in sorted(models.rglob("*.yaml")) if path.name not in SET_DOCUMENTS]


def rewrite(models, transform):
    """Replace each generated entry span by transform(entry); return the number of documents changed."""
    changed = 0
    for path in generated_documents(models):
        text = path.read_text(encoding="utf-8")
        spans = entries(text)
        head = text[: spans[0].start] if spans else text
        updated = head + "".join(transform(entry) for entry in spans)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def strip_comments(text, source):
    """Blank comments and attributes, keeping offsets and string literals intact."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        if text[i] in "'\"":
            i = skip_string(text, i)
            continue
        end = comment_end(text, i, source)
        if end is None:
            i += 1
            continue
        for j in range(i, end):
            if out[j] != "\n":
                out[j] = " "
        i = end
    return "".join(out)


def comment_end(text, i, source):
    """The end offset of the comment or attribute starting at i, or None."""
    if text.startswith("/*", i):
        end = text.find("*/", i + 2)
        return len(text) if end < 0 else end + 2
    if text.startswith("#[", i):
        return matching(text, i + 1, source) + 1
    if text.startswith("//", i) or text[i] == "#":
        end = text.find("\n", i)
        return len(text) if end < 0 else end
    return None


def skip_string(text, i):
    quote, j = text[i], i + 1
    while j < len(text) and text[j] != quote:
        j += 2 if text[j] == "\\" else 1
    return j + 1


def matching(text, i, source):
    """The offset of the bracket closing the one at i, skipping string literals."""
    depth, j = 0, i
    while j < len(text):
        if text[j] in "'\"":
            j = skip_string(text, j)
            continue
        depth += (text[j] in OPENERS) - (text[j] in CLOSERS)
        if depth == 0:
            return j
        j += 1
    raise ExtractionFailure(f"{source}: unbalanced bracket at offset {i}")


def split_top_level(text):
    """Split on commas outside brackets and string literals."""
    parts, depth, start, j = [], 0, 0, 0
    while j < len(text):
        if text[j] in "'\"":
            j = skip_string(text, j)
            continue
        depth += (text[j] in OPENERS) - (text[j] in CLOSERS)
        if text[j] == "," and depth == 0:
            parts.append(text[start:j])
            start = j + 1
        j += 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]
