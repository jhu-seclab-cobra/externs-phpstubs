# PHP Stubs — Taint Document Set Design

The classpath roots, the opener consumers and the loader share, and the
layout of the generated taint document set. Concepts:
[concept-taint.md](concept-taint.md). Registry types: [design.md](design.md).

## Design Overview

- **Classes:** `StubResources` (object)
- **External types (commons-phpmodels):** `ResourceOpener`,
  `DocumentSetLoader`, `DocumentSet`, `CategoryMapping`, `Vocabulary`
- **Relationships:** `StubResources` creates `ResourceOpener` instances;
  the bundled `MountSequence` opens every set root through `StubResources`;
  a consumer loading one set alone passes the opener to `DocumentSetLoader`. One-way; `StubResources` depends on nothing in this
  module.
- **Exceptions:** none of its own. A consumer's set load raises the
  commons-phpmodels exceptions unchanged.
- **Dependency roles:** Constants and factory: `StubResources`. Loader of
  the taint set: commons-phpmodels (never this module at runtime).

Package `edu.jhu.cobra.externs.phpstubs`, public.

## Class / Type Specifications

### StubResources (object)

**Responsibility:** Names the bundled classpath roots and builds the one
opener that reads under a root. The taint set has no registry, facade, or
entry type here: its consumer is the format library's set loader.

**State:** `const val MODELS = "/models/"`, `const val TAINT = "/taint/"`,
`const val TAINT_RULES = "/taint-rules/"`, `const val VALUE_RULES = "/value-rules/"`
— value tier: constants, fixed by the resource layout. The hand-maintained sets:
[design-taint-rules.md](design-taint-rules.md), [design-value-rules.md](design-value-rules.md).

**Methods:**
- `opener(root: String): ResourceOpener`
  - **Behavior:** returns an opener that resolves `root + path` on the
    classpath of this module; trailing slash on `root` optional.
  - **Input:** a classpath directory.
  - **Output:** an opener yielding a fresh stream per call, `null` when the
    resource is absent.
  - **Errors:** none.

## Resource Layout

```
taint/
├── index.txt          # build-generated manifest: sanitizers.yaml, sinks.yaml, sources.yaml
├── provenance.yaml    # producer tools/extract_taint.py over vimeo/psalm 5.6.0; verification generated
├── vocabulary.yaml    # psalm's taint kinds as categories; origin `input`
├── policy.yaml        # one row: input enables every kind of psalm's input group
├── sinks.yaml         # dictionary + @psalm-taint-sink: one entry per subject
├── sanitizers.yaml    # @psalm-taint-escape: one entry per (subject, condition)
└── sources.yaml       # superglobals + @psalm-taint-source: one entry per subject
```

Every document carries the producer header naming the psalm release and
the script; `provenance.yaml` states the same producer as data. Entry forms:

| Document | Subject kinds | Body | Condition |
|----------|---------------|------|-------|
| sinks.yaml | function, method | `sinks`: one `(argument(n), kind)` per dangerous argument, ports ascending, kinds in psalm order | none |
| sanitizers.yaml | function, method | `sanitizers`: one declaration with the escaped kinds | `when: [_, <int>]` (a wildcard per earlier position) for a conditional escape |
| sources.yaml | variable, method | `sources`: one declaration producing `input` | none |

No entry declares a signature: the set states psalm's assertions, not
declarations, so no arity check applies and a subject absent from the
registry is admitted. Entries are sorted by subject spelling, then condition
value. A variadic dangerous parameter is stated at its own position only.

## Extraction

`tools/extract_taint.py` (Python 3, standard library) reads one psalm
checkout and writes every file of the set except the manifest:

| Input (relative to the psalm root) | Yields |
|------------------------------------|--------|
| `src/Psalm/Type/TaintKind.php` | category names, in declaration order |
| `src/Psalm/Type/TaintKindGroup.php` (`ALL_INPUT`) | the policy row's `enables` |
| `dictionaries/InternalTaintSinkMap.php` | sinks by argument position |
| `stubs/**/*.phpstub` docblocks | `@psalm-taint-sink kind $param` → sink at the parameter's position; `@psalm-taint-escape kind` → sanitizer; `@psalm-taint-escape ($param is N ? 'kind' : null)` → conditional sanitizer; `@psalm-taint-source input` → source |
| `.../Fetch/VariableFetchAnalyzer.php` | the superglobal names psalm colors |

Arguments: `--psalm <root>`, `--out <taint dir>`; the psalm version is read
from the checkout's Composer metadata when present. A parameter name that
does not occur in the stub signature, or a kind absent from `TaintKind`,
aborts the run. Output is deterministic: same input, identical bytes.

## Validation Rules

- The set decodes under its own vocabulary with no mapping: every kind
  and origin an entry names is declared in `vocabulary.yaml`.
- Every entry declares no signature and exactly one of the three taint
  sections.
- Consumers load with a mapping that lists every category and origin the
  set uses; an unlisted name is the format library's `VocabularyException`.
- The repository tests, not the consumer, prove the set decodes.
