# PHP Stubs — Rules Document Set Design

The classpath root and layout of the hand-maintained rules document set.
Concepts: [concept-rules.md](concept-rules.md). The opener and the taint
set: [design-taint.md](design-taint.md).

## Design Overview

- **Classes:** `StubResources` (object; the `RULES` constant only)
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `CategoryMapping`, `Vocabulary`
- **Relationships:** consumers pass `StubResources.opener(StubResources.RULES)`
  to `DocumentSetLoader` with the taint set's vocabulary (or their own
  vocabulary plus a mapping) as context. Nothing in this module reads the
  set at runtime.
- **Exceptions:** none of its own.

## Class / Type Specifications

### StubResources (object), addition

**State:** `const val RULES = "/rules/"` — value tier: constant, fixed by
the resource layout. `MODELS`, `TAINT`, and `opener`: [design-taint.md](design-taint.md).

## Resource Layout

```
rules/
├── index.txt          # build-generated manifest: sanitizers.yaml, sinks.yaml, sources.yaml
├── vocabulary.yaml    # additions only: kind `xpath`, color `external`
├── policy.yaml        # input enables xpath; external enables every input kind and xpath
├── sinks.yaml         # Argus sinks the format expresses; widened psalm subjects restate psalm's points
├── sanitizers.yaml    # escapes psalm lacks: shell, html, sql, file, and value-typing escapes for every kind
└── sources.yaml       # `input` for request data psalm does not color; `external` for environment and stored data
```

Every document carries a header naming its provenance. Entry forms match
the taint set's table in [design-taint.md](design-taint.md); the set adds
no guarded entry. Entries are sorted by subject spelling.

| Document | Subject kinds | Content |
|----------|---------------|---------|
| sinks.yaml | function, method | one entry per subject with every kind it sinks, ports ascending, kinds in psalm order; receiver-triggered sinks omitted |
| sanitizers.yaml | function | one declaration per subject; a value-typing escape (`intval`, `md5`, ...) names every kind |
| sources.yaml | variable, function, method | one declaration per subject producing `input` or `external` |

## Validation Rules

- The set decodes over the taint set's vocabulary with no mapping and
  fails to decode alone: its vocabulary declares only the additions.
- Every entry is a `SubjectModel` with no signature and exactly one of
  the three taint sections.
- No entry's section equals the taint set's section for the same subject
  and guard.
- A sinks entry whose subject the taint set also sinks contains every one
  of the taint set's sink points.
- A consumer's mapping lists every psalm kind, `xpath`, `input`, and
  `external`; an unlisted name is the format library's `VocabularyException`.
- The repository tests, not the consumer, prove the set decodes.

## Maintenance

The set is edited by hand. A new sink is one entry with all of its kinds;
a subject the taint set already sinks copies psalm's points before adding
its own. A new kind or color is declared in `vocabulary.yaml` and enabled
in `policy.yaml` before any document names it.
