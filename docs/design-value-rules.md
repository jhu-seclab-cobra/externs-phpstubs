# PHP Stubs — Value Rules Document Set Design

The classpath root and layout of the hand-maintained value rules document
set. Concepts: [concept-value-rules.md](concept-value-rules.md). The
opener and the taint set: [design-taint.md](design-taint.md).

## Design Overview

- **Classes:** `StubResources` (object; the `VALUE_RULES` constant only)
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `SetProvenance`, `Verification`
- **Relationships:** consumers pass `StubResources.opener(StubResources.VALUE_RULES)`
  to `DocumentSetLoader` with no context and no mapping. Nothing in this
  module reads the set at runtime.
- **Exceptions:** none of its own.

## Class / Type Specifications

### StubResources (object), addition

**State:** `const val VALUE_RULES = "/value-rules/"` — value tier: constant,
fixed by the resource layout. `MODELS`, `TAINT`, `TAINT_RULES`, and `opener`:
[design-taint.md](design-taint.md).

## Resource Layout

```
value-rules/
├── index.txt             # build-generated manifest: the thirteen area documents
├── provenance.yaml       # producer: externs-phpstubs review against the PHP manual; verification: manual
├── strings-transform.yaml, strings-inspect.yaml, strings-format.yaml
├── variable.yaml, array.yaml, filesystem.yaml, database.yaml
├── execution.yaml, funchand.yaml, encoding.yaml, environment.yaml
└── math.yaml, datetime.yaml
```

Every document carries a header naming the set and its PHP manual area.
Entries are flat: `subject`, optional `when`, `returns`, optional
`propagation`. Entries are sorted by subject spelling; a guarded branch
precedes its default branch. A review reason is a `#` comment line
directly above the entry it justifies.

| Document group | Subject kinds | Content |
|----------------|---------------|---------|
| strings-* | function | length, comparison, search, hashing, transformation, formatting; `echo` and `print` |
| variable, array | function | conversions, type tests, `isset`, `empty`, `print_r` and `var_export` branches |
| filesystem, database, execution, funchand, encoding, environment, math, datetime | function | typed results and flow sets by PHP manual area; `eval` |

## Validation Rules

- The set decodes with no context: it names no category and no color, and
  its vocabulary and policy are absent.
- `provenance.yaml` decodes to verification `manual`.
- Every entry is a `SubjectModel` with no signature, a `returns` section,
  and no taint section.
- Every subject is a function or method the registry declares.
- No default-branch unit equals the registry entry's unit for the same
  subject.
- The repository tests, not the consumer, prove the set decodes.

## Maintenance

The set is edited by hand. A new rule states one subject the registry
declares, with the whole unit. A rule whose unit differs from the
generated one, or that narrows the declared return type, is checked
against the PHP manual and carries the reason as a comment; a rule the
manual shows the generated declaration already states correctly is not
added. A subject the registry lacks is an extraction task in `todo.md`,
never a rule.
