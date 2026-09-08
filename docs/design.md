# PHP Stubs — Design

The data side of the library: the resource roots, the five bundled sets and
their fixed Merge Order, the corpus rules on the generated set, and the
error types. The lookup surface — merge, records, facts, `PhpStubs` — is in
[design-lookup.md](design-lookup.md). Concepts: [concept.md](concept.md),
[concept-lookup.md](concept-lookup.md). Domain semantics:
[model-lookup.md](model-lookup.md). Fold: [spec-merge.md](spec-merge.md).

## Design Overview

- **Classes:** `StubResources` (object), `PhpStubs`, `BuiltinRecord<S>`,
  the five fact types, `Merge`, `Mount` ([design-lookup.md](design-lookup.md))
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `Document`, `ResourceOpener`, `CategoryMappingLoader`,
  `CategoryMapping`, `ModelEntry`, `ModelSubject` and its seven subtypes,
  `ArgPattern`, `SignatureInfo` and its four subtypes, `Vocabulary`,
  `TaintPolicy`, `Precedence`, `Verification`
- **Relationships:** `StubResources` names the roots and opens them;
  `PhpStubs` mounts the bundled roots in Merge Order through
  `DocumentSetLoader` (the psalm mapping decoded once by
  `CategoryMappingLoader` and applied to the two psalm-named sets) and
  folds them in `Merge`. One-way: facade → merge → format library.
- **Exceptions:** `StubIndexNotFoundException`, `StubIndexInvalidException`
  (both extend `RuntimeException`).
- **Dependency roles:** Resource roots and opener: `StubResources`.
  Facade and composition root: `PhpStubs`. Decoder and validator:
  commons-phpmodels.

Package `edu.jhu.cobra.externs.phpstubs`, one module, `explicitApi()`.
commons-phpmodels is an `api` dependency: its subject, signature, section,
and condition types are the record surface. No YAML library is a direct
dependency.

## Class / Type Specifications

### StubResources (object)

**Responsibility:** The classpath roots of every bundled set and the
opener over a root. Value tier: constants, because the layout is fixed by
this repository's build.

**Constants:** `MODELS = "/models/"`, `VALUE_RULES = "/value-rules/"`,
`VOCABULARY = "/vocabulary/"`, `TAINT = "/taint/"`,
`TAINT_RULES = "/taint-rules/"`, `PSALM_MAPPING = "/vocabulary/psalm-mapping.yaml"`.

**Methods:**
- `opener(root: String): ResourceOpener` — resolves a relative document
  path against `root` (trailing slash optional) through
  `Class.getResourceAsStream`; returns `null` for an absent resource.
  `MountSequence` records absences to raise `StubIndexNotFoundException`.

### Merge Order (private `bundledMounts()` of `PhpStubs.kt`)

The bundled mounts, in this order, each with its mapping:

| Position | Root | Mapping | Verification |
|----------|------|---------|--------------|
| 0 | `MODELS` | none | from `models/provenance.yaml` (generated) |
| 1 | `VALUE_RULES` | none | from its provenance (manual) |
| 2 | `VOCABULARY` | none | from its provenance (manual); empty manifest |
| 3 | `TAINT` | `PSALM_MAPPING` | from its provenance (generated) |
| 4 | `TAINT_RULES` | `PSALM_MAPPING` | from its provenance (manual) |

Each set decodes against the vocabulary accumulated over the earlier
positions; a set's own `vocabulary.yaml` merges after it decodes and its
`policy.yaml` rows append. A bundled set without `provenance.yaml` is a
packaging fault, not a default.

**Corpus rules on the generated set** (position 0; each violation is a
`StubIndexInvalidException` naming the document and subject):
- No entry has a `VariableSubject`; predefined variables are not stubs.
- Every entry declares a `signature` and no condition.
- No two documents declare the same subject; the message names both.

Constant subjects fold nothing, so `TRUE` and `true` are distinct entries.
The extension of each generated entry is data tier: derived from the
document's placement, never a constant in code.

The other four sets follow their own set rules
([design-taint.md](design-taint.md), [design-taint-rules.md](design-taint-rules.md),
[design-value-rules.md](design-value-rules.md)) and the format library's
duplicate rule per (subject, condition) within one document.

## Resource Layout

```
models/
├── index.txt              # build-generated manifest, sorted relative paths
├── provenance.yaml        # producer tools/convert_stubs.py v2; verification generated
├── core.yaml              # extension "core"
├── language/              # hand-declared language constructs
│   ├── keyword.yaml       # 14 keyword functions + class exit, extension "keyword"
│   ├── scalar.yaml        # classes int, float, string, bool, array, extension "scalar"
│   └── legacy.yaml        # class resource, extension "legacy"
├── manual/<extension>.yaml       # hand-declared built-ins the extraction omits: mysqli, pdo, sqlite3, mysql, standard
├── standard/standard_1..8.yaml   # extension "standard" (split suffix removed)
└── <category>/<extension>.yaml   # crypto, database, file, image, misc, network, system, text, xml
vocabulary/
├── index.txt              # comment only: the set ships no model document
├── provenance.yaml        # producer externs-phpstubs canonical vocabulary; verification manual
├── vocabulary.yaml        # twelve danger categories, two origin colors, with descriptions
├── policy.yaml            # both colors enable every category
└── psalm-mapping.yaml     # psalm kinds → canonical names; has_quotes, cookie, user_secret, system_secret → ignore
```

Generated documents carry the producer header of commons-phpmodels'
generated layer and are never hand-edited; language, manual, and
vocabulary documents are hand-maintained without one. A keyword function
declares one optional variadic `mixed` parameter and a `mixed` return; a
language class declares `classifier: class`. A manual entry declares its
PHP-manual signature and, where the manual states a flow, a propagation;
the reason is a comment.

The Gradle resource task writes `index.txt` for `models/`, `taint/`,
`taint-rules/`, `value-rules/` (main) and `models-test/` (test), listing
every document except `vocabulary.yaml`, `policy.yaml`, `provenance.yaml`,
and `psalm-mapping.yaml`; `vocabulary/index.txt` and every other test
fixture directory ship their own manifest. Set layouts:
[design-taint.md](design-taint.md), [design-taint-rules.md](design-taint-rules.md),
[design-value-rules.md](design-value-rules.md).

## Exception / Error Types

| Exception | When raised |
|-----------|-------------|
| `StubIndexNotFoundException(resource)` | `index.txt`, a listed document, or the psalm mapping resource is not on the classpath or under an extension directory |
| `StubIndexInvalidException(reason, cause?)` | The set load or merge fails for any other reason (commons-phpmodels cause attached), a bundled set ships without `provenance.yaml`, a corpus rule is violated, or a conditional entry declares a signature |
| `IllegalArgumentException` | A lookup name is not a PHP identifier spelling (raised by the commons-phpmodels subject creator) |

Every bundled-set error surfaces on first access to `PhpStubs`; an
extension-set error surfaces from the `with` call that mounts it.

## Validation Rules

- Format validation — YAML strictness, subject spellings, signature shape,
  arity against the parameter list and the condition's positions, declared
  types, vocabulary references, mapping totality — is commons-phpmodels'
  and is not repeated here.
- The corpus rules run over the generated set before the fold; a violation
  fails the whole load.
- Duplicate detection compares subjects, so `Exception` and `exception`
  collide (folded kind) while `TRUE` and `true` do not (sensitive kind).
- `index.txt` lists relative document paths, one per line, sorted; blank
  lines and `#` comments are skipped; a path listed twice fails the load
  (commons-phpmodels rule).
- The bundled `vocabulary.yaml` declares every name `VulnClass` and
  `Origin` enumerate, and no other; the psalm mapping lists every kind the
  two psalm-named sets use.
