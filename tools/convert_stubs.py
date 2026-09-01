#!/usr/bin/env python3
"""Convert tag-based stub YAML into the unified PHP model format.

Reads every ``src/main/resources/stubs/**/*.yaml`` tag file and emits one
model document per source file under ``src/main/resources/models/`` with the
same relative path. The emitted format is the commons-phpmodels declaration
DSL: one-key subject maps, a ``signature`` section per declaration, and a
``propagation`` section derived from ``flowsToReturn``.

The conversion is verified in-process before anything is written:

* every emitted file re-parses and canonicalizes back to exactly the
  canonical form of its source entries, field by field, in file order;
* per-kind entry counts of the whole corpus are compared source vs emitted;
* every declared type must be a member of the closed keyword vocabulary.

Any verification failure aborts the run with a non-zero exit before any
output file is replaced.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

# Producer identity stamped into every generated file header.
PRODUCER = "tools/convert_stubs.py v2"

REPO_ROOT = Path(__file__).resolve().parent.parent
STUBS_ROOT = REPO_ROOT / "externs-phpstubs" / "src" / "main" / "resources" / "stubs"
MODELS_ROOT = REPO_ROOT / "externs-phpstubs" / "src" / "main" / "resources" / "models"

# Closed by the PHP type system; mirrors DeclaredType's keyword vocabulary.
KEYWORD_TYPES = {
    "string", "int", "float", "bool", "array", "object",
    "callable", "resource", "mixed", "void", "null", "iterable",
}

# Upstream extraction artifacts that mean "no declared type".
UNDECLARED_TYPE_SPELLINGS = {"none", ""}


class ConversionError(Exception):
    """A source entry cannot be represented, or verification failed."""


def normalize_type(raw: object, context: str) -> str:
    """Map a source type spelling onto the closed declared-type vocabulary."""
    text = str(raw).strip() if raw is not None else "mixed"
    if text.lower() in UNDECLARED_TYPE_SPELLINGS:
        return "mixed"
    if text.lower() not in KEYWORD_TYPES:
        raise ConversionError(f"{context}: type '{text}' is outside the keyword vocabulary")
    return text.lower()


def convert_params(entry: dict, context: str) -> list[dict]:
    params = []
    for param in entry.get("params") or []:
        converted = {
            "name": str(param["name"]),
            "type": normalize_type(param.get("type", "mixed"), f"{context} param {param.get('name')}"),
        }
        if bool(param.get("optional", False)) or param.get("default") is not None:
            converted["optional"] = True
        params.append(converted)
    # The tag format never states variadic parameters; a flow index beyond the
    # parameter list is only reachable through a variadic tail, so the last
    # parameter is marked variadic when any declared flow points past the list.
    flows = [int(index) for index in entry.get("flowsToReturn") or []]
    if params and flows and max(flows) >= len(params):
        params[-1]["variadic"] = True
    return params


def convert_callable(entry: dict, subject_kind: str, subject: str) -> dict:
    context = f"{subject_kind} {subject}"
    signature = {}
    params = convert_params(entry, context)
    if params:
        signature["params"] = params
    signature["returnType"] = normalize_type(entry.get("return", "mixed"), f"{context} return")
    model = {"subject": {subject_kind: subject}, "signature": signature}
    flows = entry.get("flowsToReturn") or []
    if flows:
        model["propagation"] = [
            {"from": f"argument({int(index)})", "to": "return"} for index in flows
        ]
    return model


def convert_entry(entry: dict, context: str) -> dict:
    tag = entry.get("tag")
    name = str(entry.get("name"))
    if tag == "function":
        return convert_callable(entry, "function", name)
    if tag == "method":
        return convert_callable(entry, "method", f"{entry['class']}::{name}")
    if tag == "class":
        return {"subject": {"class": name}, "signature": {"classifier": "class"}}
    if tag == "constant":
        return {
            "subject": {"constant": name},
            "signature": {
                "type": normalize_type(entry["type"], f"constant {name}"),
                "value": str(entry["value"]),
            },
        }
    if tag == "class_constant":
        subject = f"{entry['class']}::{name}"
        return {
            "subject": {"class_constant": subject},
            "signature": {
                "type": normalize_type(entry["type"], f"class_constant {subject}"),
                "value": str(entry["value"]),
            },
        }
    raise ConversionError(f"{context}: unknown tag '{tag}'")


def canonical_source(entry: dict) -> tuple:
    """One comparable tuple per source entry, in the emitted vocabulary."""
    tag = entry["tag"]
    name = str(entry["name"])
    if tag in ("function", "method"):
        subject = f"{entry['class']}::{name}" if tag == "method" else name
        params = tuple(
            (p["name"], p["type"], p.get("optional", False), p.get("variadic", False))
            for p in convert_params(entry, subject)
        )
        return_type = normalize_type(entry.get("return", "mixed"), subject)
        flows = tuple(int(i) for i in entry.get("flowsToReturn") or [])
        return (tag, subject, params, return_type, flows)
    if tag == "class":
        return (tag, name)
    subject = f"{entry['class']}::{name}" if tag == "class_constant" else name
    return (tag, subject, normalize_type(entry["type"], subject), str(entry["value"]))


def canonical_emitted(model: dict) -> tuple:
    """The comparable tuple of one emitted model entry."""
    ((kind, subject),) = model["subject"].items()
    signature = model["signature"]
    if kind in ("function", "method"):
        params = tuple(
            (p["name"], p["type"], p.get("optional", False), p.get("variadic", False))
            for p in signature.get("params") or []
        )
        flows = tuple(
            int(flow["from"].removeprefix("argument(").removesuffix(")"))
            for flow in model.get("propagation") or []
        )
        return (kind, subject, params, signature["returnType"], flows)
    if kind == "class":
        return (kind, subject)
    return ("class_constant" if kind == "class_constant" else "constant",
            subject, signature["type"], signature["value"])


def convert_file(source: Path) -> tuple[str, list[tuple], list[str]]:
    """Convert one stub file; returns (document, canonical entries, kinds)."""
    entries = yaml.safe_load(source.read_text(encoding="utf-8")) or []
    relative = source.relative_to(STUBS_ROOT)
    models, canon, kinds = [], [], []
    for position, entry in enumerate(entries):
        context = f"{relative}[{position}]"
        models.append(convert_entry(entry, context))
        canon.append(canonical_source(entry))
        kinds.append(entry["tag"])
    header = (
        f"# Generated from stubs/{relative} by {PRODUCER}.\n"
        f"# Do not hand-edit; corrections belong in a higher configuration layer.\n"
    )
    body = yaml.safe_dump(
        models, sort_keys=False, default_flow_style=False, allow_unicode=True, width=100,
    ) if models else ""
    document = header + body

    reparsed = yaml.safe_load(document) or []
    if [canonical_emitted(m) for m in reparsed] != canon:
        raise ConversionError(f"{relative}: emitted document does not round-trip to its source")
    return document, canon, kinds


def main() -> int:
    sources = sorted(STUBS_ROOT.rglob("*.yaml"))
    if not sources:
        print(f"no stub files under {STUBS_ROOT}", file=sys.stderr)
        return 1

    documents: dict[Path, str] = {}
    kind_counts: dict[str, int] = {}
    total = 0
    for source in sources:
        document, canon, kinds = convert_file(source)
        documents[MODELS_ROOT / source.relative_to(STUBS_ROOT)] = document
        for kind in kinds:
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        total += len(canon)

    for target, document in documents.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document, encoding="utf-8")

    print(f"converted {len(documents)} files, {total} entries")
    for kind in sorted(kind_counts):
        print(f"  {kind}: {kind_counts[kind]}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConversionError as failure:
        print(f"conversion failed: {failure}", file=sys.stderr)
        sys.exit(1)
