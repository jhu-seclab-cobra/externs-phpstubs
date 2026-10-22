# PHP Stubs — Value Rules Document Set Design

The classpath root and layout of the hand-maintained value rules document
set. Concepts: [concept-value-rules.md](concept-value-rules.md). The
opener and the taint set: [design-taint.md](design-taint.md).

## Design Overview

- **Classes:** `StubResources` (object; the `VALUE_RULES` constant only)
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `SetProvenance`, `Verification`
- **Relationships:** `PhpStubs` mounts the set at position 1, unmapped
  ([design.md](design.md) Mount Order).
- **Exceptions:** none of its own.

## Class / Type Specifications

### StubResources (object), addition

**State:** `const val VALUE_RULES = "/value-rules/"` — value tier: constant,
fixed by the resource layout. `MODELS`, `TAINT`, `TAINT_RULES`, and `opener`:
[design-taint.md](design-taint.md).

## Resource Layout

```
value-rules/
├── index.txt             # build-generated manifest: the fifteen area documents
├── provenance.yaml       # producer: externs-phpstubs review against the PHP manual; verification: manual
├── strings-transform.yaml, strings-inspect.yaml, strings-format.yaml
├── variable.yaml, array.yaml, filesystem.yaml, database.yaml
├── execution.yaml, funchand.yaml, encoding.yaml, environment.yaml
├── math.yaml, datetime.yaml, exceptions.yaml
└── spl.yaml
```

Every document carries a header naming the set and its PHP manual area.
Entries are flat: `subject`, optional `when`, `returns`, optional
`propagation`, optional `characters`. Entries are sorted by subject spelling; a conditional entry
precedes the unconditional entry of its subject. A review reason is a `#` comment line
directly above the entry it justifies.

| Document group | Subject kinds | Content |
|----------------|---------------|---------|
| strings-* | function | length, comparison, search, hashing, transformation, formatting; `echo` and `print` |
| variable, array | function | conversions, type tests, `isset`, `empty`, `print_r` and `var_export` branches; the flows into and out of the callback of `array_map`, `array_filter`, `array_reduce`, `array_walk` and `usort` |
| filesystem, database, execution, funchand, encoding, environment, math, datetime | function, method | typed results and flow sets by PHP manual area, with the callback flows of `call_user_func`, `call_user_func_array` and `register_tick_function`; `eval`; the query methods of `mysqli`, `PDO`, `SQLite3` |
| exceptions | method | the message flow from the constructor's message argument into the receiver, and from the receiver into the `getMessage` result |
| spl | method | the stored value argument into the receiver, and the receiver into the element-returning methods of the SPL containers; the receiver is one abstract value, so a read of a container that ever held a tainted value is tainted; subclasses reach the rules through the declared parent |

## Validation Rules

- The set decodes with no context: it names no vulnerability type and no source kind, and
  its vocabulary and policy are absent.
- `provenance.yaml` decodes to verification `manual`.
- Every entry declares no signature, a `returns` section,
  and no taint section.
- Every subject is a function or method the generated set declares.
- No unconditional entry's unit equals the generated entry's unit for the
  same subject.
- A callback port names a parameter of the subject's merged signature whose
  type admits `callable`; what a callback port means is defined in
  commons-phpmodels `docs/model.md` Port.
- The repository tests, not the consumer, prove the set decodes.

## Maintenance

The set is edited by hand. A new rule states one subject the generated set
declares, with the whole unit. A rule whose unit differs from the
generated one, or that narrows the declared return type, is checked
against the PHP manual and carries the reason as a comment; a rule the
manual shows the generated entry already states correctly is not
added. A subject the generated set lacks is an extraction task in `todo.md`,
never a rule.
