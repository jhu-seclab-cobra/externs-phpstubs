#!/usr/bin/env python3
"""Emit the taint document set from one psalm checkout (design-taint.md, Extraction).

Reads psalm's taint kinds, the input kind group, the internal sink dictionary,
the taint annotations in psalm's stubs, and the superglobal source rule, and
writes vocabulary.yaml, policy.yaml, sinks.yaml, sanitizers.yaml, and
sources.yaml under the output directory. index.txt is written by Gradle.
"""

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

SCRIPT = "tools/extract_taint.py"
ORIGIN = "input"

KIND_DESCRIPTIONS = {
    "callable": "Callable name resolved and invoked",
    "unserialize": "Serialized payload passed to unserialize",
    "include": "Path passed to include or require",
    "eval": "PHP code passed to eval or create_function",
    "ldap": "LDAP filter or DN text",
    "sql": "SQL query text",
    "html": "HTML output",
    "has_quotes": "Text carrying quote characters into an HTML attribute",
    "shell": "Shell command text",
    "ssrf": "URL fetched by the server",
    "file": "File system path",
    "cookie": "Cookie name or value",
    "header": "HTTP response header text",
    "user_secret": "Secret belonging to one user",
    "system_secret": "Secret belonging to the system",
}

ORIGIN_DESCRIPTION = "Attacker-controlled input from colored superglobals and annotated sources"

TAINT_KIND = "src/Psalm/Type/TaintKind.php"
TAINT_GROUP = "src/Psalm/Type/TaintKindGroup.php"
SINK_MAP = "dictionaries/InternalTaintSinkMap.php"
STUBS = "stubs"
VARIABLE_FETCH = "src/Psalm/Internal/Analyzer/Statements/Expression/Fetch/VariableFetchAnalyzer.php"

CLASS_DECL = re.compile(r"^\s*(?:abstract\s+|final\s+)*(?:class|interface|trait)\s+(\w+)")
FUNCTION_DECL = re.compile(r"^(\s*)(?:(?:public|protected|private|static|final|abstract)\s+)*function\s+&?(\w+)\s*\(")
SINK_TAG = re.compile(r"@psalm-taint-sink\s+(\w+)\s+\$(\w+)")
ESCAPE_TAG = re.compile(r"@psalm-taint-escape\s+(\w+)\s*$")
GUARDED_ESCAPE_TAG = re.compile(r"@psalm-taint-escape\s+\(\$(\w+)\s+is\s+(\d+)\s+\?\s+'(\w+)'\s+:\s+null\)")
SOURCE_TAG = re.compile(r"@psalm-taint-source\s+(\w+)")
PARAM = re.compile(r"\$(\w+)")


def fail(message):
    sys.exit(f"extract_taint: {message}")


def read(root, relative):
    path = root / relative
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def psalm_version(root):
    installed = root.parent.parent / "composer" / "installed.json"
    if not installed.is_file():
        return "unknown"
    data = json.loads(installed.read_text(encoding="utf-8"))
    packages = data["packages"] if isinstance(data, dict) else data
    for package in packages:
        if package.get("name") == "vimeo/psalm":
            return package.get("version", "unknown")
    return "unknown"


def taint_kinds(root):
    kinds = re.findall(r"public const \w+ = '(\w+)';", read(root, TAINT_KIND))
    if not kinds:
        fail("no taint kinds found")
    return kinds


def input_group(root):
    text = read(root, TAINT_GROUP)
    block = re.search(r"ALL_INPUT = \[(.*?)\];", text, re.S)
    if not block:
        fail("ALL_INPUT group not found")
    constants = re.findall(r"TaintKind::(\w+)", block.group(1))
    names = dict(re.findall(r"public const (\w+) = '(\w+)';", read(root, TAINT_KIND)))
    return [names[constant] for constant in constants]


def superglobals(root):
    names = re.findall(r"\$var_name === '(\$_\w+)'", read(root, VARIABLE_FETCH))
    if not names:
        fail("superglobal source rule not found")
    return sorted(set(names))


def sink_dictionary(root):
    """Subject -> list of (position, kind) from InternalTaintSinkMap.php."""
    result = OrderedDict()
    for name, groups in re.findall(r"^'([\w:]+)' => \[(.*)\],?$", read(root, SINK_MAP), re.M):
        positions = re.findall(r"\[([^\[\]]*)\]", groups)
        for position, group in enumerate(positions):
            for kind in re.findall(r"'(\w+)'", group):
                result.setdefault(name, []).append((position, kind))
    if not result:
        fail("sink dictionary is empty")
    return result


def parameter_positions(signature):
    depth = 0
    parts, current = [], ""
    for char in signature:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    positions = {}
    for index, part in enumerate(parts):
        found = PARAM.search(part)
        if found:
            positions[found.group(1)] = index
    return positions


def stub_annotations(root):
    """Yield (subject, tags, positions) for every annotated stub declaration."""
    for path in sorted((root / STUBS).rglob("*.phpstub")):
        current_class = None
        doc = None
        lines = path.read_text(encoding="utf-8").splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if stripped.startswith("/**"):
                doc = []
            if doc is not None:
                doc.append(line)
                if stripped.endswith("*/"):
                    pending, doc = doc, None
                    index += 1
                    index, declaration = collect_declaration(lines, index)
                    if declaration is not None:
                        class_match = CLASS_DECL.match(declaration)
                        if class_match:
                            current_class = class_match.group(1)
                        else:
                            yield from annotated(declaration, pending, current_class, path)
                    continue
                index += 1
                continue
            class_match = CLASS_DECL.match(line)
            if class_match:
                current_class = class_match.group(1)
            index += 1


def collect_declaration(lines, index):
    """Return (next index, declaration text) for the declaration following a docblock."""
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        return index, None
    text = lines[index]
    if FUNCTION_DECL.match(text):
        while ")" not in text and index + 1 < len(lines):
            index += 1
            text += " " + lines[index].strip()
    return index + 1, text


def annotated(declaration, doc, current_class, path):
    function = FUNCTION_DECL.match(declaration)
    if function is None:
        return
    tags = [line.strip(" *") for line in doc if "@psalm-taint-" in line]
    if not tags:
        return
    indent, name = function.group(1), function.group(2)
    subject = name if not indent or current_class is None else f"{current_class}::{name}"
    signature = declaration[declaration.index("(") + 1 : declaration.rindex(")")]
    yield subject, tags, parameter_positions(signature), path


def collect(root):
    kinds = taint_kinds(root)
    sinks = OrderedDict()
    sanitizers = OrderedDict()
    sources = OrderedDict()

    def kind_checked(kind, where):
        if kind not in kinds:
            fail(f"unknown taint kind '{kind}' in {where}")
        return kind

    for subject, entries in sink_dictionary(root).items():
        for position, kind in entries:
            sinks.setdefault(subject, set()).add((position, kind_checked(kind, SINK_MAP)))
    for subject, tags, positions, path in stub_annotations(root):
        for tag in tags:
            sink = SINK_TAG.search(tag)
            guarded = GUARDED_ESCAPE_TAG.search(tag)
            escape = ESCAPE_TAG.search(tag)
            source = SOURCE_TAG.search(tag)
            if sink:
                kind, param = sink.groups()
                if param not in positions:
                    fail(f"parameter ${param} not in signature of {subject} ({path})")
                sinks.setdefault(subject, set()).add((positions[param], kind_checked(kind, path)))
            elif guarded:
                param, value, kind = guarded.groups()
                if param not in positions:
                    fail(f"parameter ${param} not in signature of {subject} ({path})")
                key = (subject, positions[param], int(value))
                sanitizers.setdefault(key, set()).add(kind_checked(kind, path))
            elif escape:
                sanitizers.setdefault((subject, None, None), set()).add(kind_checked(escape.group(1), path))
            elif source:
                if source.group(1) != ORIGIN:
                    fail(f"unexpected source kind '{source.group(1)}' in {path}")
                sources.setdefault(subject, set()).add(ORIGIN)
    for name in superglobals(root):
        sources.setdefault(name, set()).add(ORIGIN)
    return kinds, sinks, sanitizers, sources


def subject_line(subject):
    if subject.startswith("$"):
        return f"    variable: {subject}"
    if "::" in subject:
        return f"    method: {subject}"
    return f"    function: {subject}"


def subject_key(subject):
    return subject.lower()


def header(version):
    return (
        f"# Generated from vimeo/psalm {version} by {SCRIPT}.\n"
        "# Do not hand-edit; re-run the script on a newer psalm release.\n"
    )


def emit_vocabulary(kinds):
    out = ["vulnClasses:"]
    for kind in kinds:
        out.append(f"  - name: {kind}")
        out.append(f"    description: {KIND_DESCRIPTIONS.get(kind, 'psalm taint kind ' + kind)}")
    out.append("provenances:")
    out.append(f"  - name: {ORIGIN}")
    out.append(f"    description: {ORIGIN_DESCRIPTION}")
    return "\n".join(out) + "\n"


def emit_policy(enables):
    return f"- origin: {ORIGIN}\n  enables: [{', '.join(enables)}]\n"


def emit_sinks(sinks, kinds):
    out = []
    for subject in sorted(sinks, key=subject_key):
        out.append("- subject:")
        out.append(subject_line(subject))
        out.append("  sinks:")
        for position, kind in sorted(sinks[subject], key=lambda item: (item[0], kinds.index(item[1]))):
            out.append(f"    - port: argument({position})")
            out.append(f"      category: {kind}")
    return "\n".join(out) + "\n"


def emit_sanitizers(sanitizers, kinds):
    out = []
    for subject, position, value in sorted(sanitizers, key=lambda key: (subject_key(key[0]), key[1] or -1, key[2] or -1)):
        out.append("- subject:")
        out.append(subject_line(subject))
        if position is not None:
            out.append("  when:")
            out.append(f"    port: argument({position})")
            out.append(f"    is: {value}")
        out.append("  sanitizers:")
        ordered = sorted(sanitizers[(subject, position, value)], key=kinds.index)
        out.append(f"    - categories: [{', '.join(ordered)}]")
    return "\n".join(out) + "\n"


def emit_sources(sources):
    out = []
    for subject in sorted(sources, key=subject_key):
        out.append("- subject:")
        out.append(subject_line(subject))
        out.append("  sources:")
        out.append(f"    - provenance: [{', '.join(sorted(sources[subject]))}]")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--psalm", required=True, type=Path, help="psalm package root")
    parser.add_argument("--out", required=True, type=Path, help="taint document set directory")
    args = parser.parse_args()
    root = args.psalm
    version = psalm_version(root)
    kinds, sinks, sanitizers, sources = collect(root)
    head = header(version)
    args.out.mkdir(parents=True, exist_ok=True)
    files = {
        "vocabulary.yaml": emit_vocabulary(kinds),
        "policy.yaml": emit_policy(input_group(root)),
        "sinks.yaml": emit_sinks(sinks, kinds),
        "sanitizers.yaml": emit_sanitizers(sanitizers, kinds),
        "sources.yaml": emit_sources(sources),
    }
    for name, body in files.items():
        (args.out / name).write_text(head + body, encoding="utf-8")
    print(f"psalm {version}: {len(sinks)} sink subjects, {len(sanitizers)} sanitizer entries, {len(sources)} source subjects")


if __name__ == "__main__":
    main()
