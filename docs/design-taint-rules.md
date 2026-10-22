# PHP Stubs — Taint Rules Document Set Design

The classpath root and layout of the hand-maintained taint rules document set.
Concepts: [concept-taint-rules.md](concept-taint-rules.md). The opener and the taint
set: [design-taint.md](design-taint.md).

## Design Overview

- **Classes:** `StubResources` (object; the `TAINT_RULES` constant only)
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `VocabularyMapping`, `Vocabulary`
- **Relationships:** `PhpStubs` mounts the set at position 4 under
  `PSALM_MAPPING` against the accumulated canonical vocabulary
  ([design.md](design.md) Mount Order).
- **Exceptions:** none of its own.

## Class / Type Specifications

### StubResources (object), addition

**State:** `const val TAINT_RULES = "/taint-rules/"` — value tier: constant, fixed by
the resource layout. `MODELS`, `TAINT`, and `opener`: [design-taint.md](design-taint.md).

## Resource Layout

```
taint-rules/
├── index.txt          # build-generated manifest: sanitizers.yaml, sinks.yaml, sources.yaml
├── provenance.yaml    # producer externs-phpstubs review of the Argus sink lists; verification manual
├── vocabulary.yaml    # additions only: kinds `xpath`, `scheme`; source kinds `external`, `path`
├── policy.yaml        # input enables xpath, scheme; external enables every input kind, xpath, scheme; path enables external's kinds but scheme
├── sinks.yaml         # Argus sink facts the format expresses, each html sink with a scheme twin; an entry for a psalm subject restates psalm's points and adds its own
├── sanitizers.yaml    # sanitizer facts psalm lacks: shell, html, sql, file, value-typing sanitizer facts for every kind; checks
└── sources.yaml       # `input` for request data psalm does not taint, `$_SERVER` split by key into `path` and `input`; `external` for environment and stored data
```

Every document carries a header naming its provenance. Entry forms match
the taint set's table in [design-taint.md](design-taint.md); the set adds
no conditional entry. Entries are sorted by subject spelling.

| Document | Subject kinds | Content |
|----------|---------------|---------|
| sinks.yaml | function, method | one entry per subject with every kind it sinks, ports ascending, kinds in psalm order; receiver-triggered sinks omitted |
| sanitizers.yaml | function | one declaration per subject; a value-typing sanitizer fact (`intval`, `md5`, ...) names every kind; a check names `argument(0)` and `accepts: true` with the `types` of a type predicate (`is_int`, `is_scalar`, ...) or the `within` class of a character check (`ctype_digit`, `is_numeric`, ...) with the kinds its class cannot carry |
| sources.yaml | variable, function, method | one declaration per subject producing `input` or `external`; `$_SERVER` holds two declarations split by `keys` |

## Validation Rules

- The set decodes over the taint set's vocabulary with no mapping and
  fails to decode alone: its vocabulary declares only the additions.
- Every entry declares no signature and exactly one of
  the three taint sections.
- No entry's section equals the taint set's section for the same subject
  and condition.
- A sinks entry whose subject the taint set also sinks contains every one
  of the taint set's sink points.
- A consumer's mapping lists every psalm kind, `xpath`, `scheme`, `input`,
  `external`, and `path`; an unlisted name is the format library's `VocabularyException`.
- The repository tests, not the consumer, prove the set decodes.

## Maintenance

The set is edited by hand. A new sink is one entry with all of its kinds;
a subject the taint set already sinks copies psalm's points before adding
its own. A new `html` sink adds its `scheme` twin on the same port. A new kind or source kind is declared in `vocabulary.yaml` and enabled
in `policy.yaml` before any document names it.
