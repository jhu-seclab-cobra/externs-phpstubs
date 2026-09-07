# PHP Stubs — Value Rules Document Set Concept

Extends [concept.md](concept.md) with the one concern it does not cover:
hand-maintained value semantics that the generated declarations lack or
state wrongly. Model entries, subjects, and the generated layer are
defined there and used here unchanged; the taint counterpart is
[concept-taint-rules.md](concept-taint-rules.md). Set provenance and
precedence are defined in commons-phpmodels `docs/concept-provenance.md`.

## 1. Context

**Problem Statement**
The generated declarations carry a value-semantics unit (returns with
propagation) only where psalm annotates a flow. For most built-ins no
annotation exists, so a consumer falls back to its conservative default:
an untyped result that every argument influences. Where an annotation
exists it is sometimes wider or narrower than the flow the PHP manual
supports. The corrections are consumer-independent facts about PHP
built-ins, yet they lived in cobraphp-core's own rule files, invisible to
any other consumer and mixed with that analyzer's configuration.

**System Role**
The value rules document set is the fourth shipped artifact of this
library: a hand-maintained classpath root in the commons-phpmodels
document-set convention holding value-semantics units only, declared
manually verified, so that a consumer ranking sets by verification lets
each unit override the generated one for its subject.

**Data Flow**
- **Inputs:** the value-semantics rules migrated from cobraphp-core,
  reviewed against the generated declarations and the PHP manual (offline).
- **Outputs:** one document set: manifest, provenance, and value documents
  grouped by PHP manual area.
- **Connections:** review → value rules document set →
  [commons-phpmodels set loader] → consumer fold by precedence.

**Scope Boundaries**
- **Owned:** the set's files, its provenance, the choice of which subjects
  it states, the rule that every stated subject exists in the generated
  declarations, the recorded reason for every unit that differs from a
  generated one, and the classpath root constant that names it.
- **Not Owned:** taint sections (the taint sets), the generated unit it
  overrides, the precedence a consumer applies, the consumer's
  conservative default, and the consumer's compute overlay.

## 2. Concepts

**Conceptual Diagram**
```
cobraphp-core rules ──review against models/ and the PHP manual──► value-rules/
                                                                    ├── index.txt
                                                                    ├── provenance.yaml  (manual)
                                                                    └── <area>.yaml      (returns + propagation only)
consumer: models/ (generated) ◄──ranked below── value-rules/ (manual), per subject and unit
```

**Core Concepts**

- **Name:** Value Rules Document Set
- **Definition:** The bundled hand-maintained document set whose every
  entry is a signature-less model asserting exactly one value-semantics
  unit: a returns classification and the exhaustive flow set into the
  result. Its provenance declares it manually verified.
- **Scope:** built-ins whose generated entry has no unit, whose generated
  unit the PHP manual contradicts, and mode-switching built-ins that need
  a guarded branch. Nothing a generated entry already states correctly.
- **Relationships:** outranks the Generated Layer under the default
  precedence; never read by the Stub Registry; sibling of the Taint Rules
  Document Set.

- **Name:** Value Rule
- **Definition:** One entry of the set. Under the format's coupling rule,
  a hand-written entry without a signature asserts the unit exhaustively:
  the returns classification and every argument-to-result flow, with an
  absent flow set meaning the result is unrelated to the arguments.
- **Scope:** function and method subjects; an optional when guard on one
  argument value selects a branch for a mode-switching built-in.
- **Relationships:** a Model Entry; its Subject must exist in the
  generated declarations (an entry for an unknown subject can never be
  selected, because existence is a signature lookup in the consumer).

- **Name:** Review Reason
- **Definition:** The PHP manual statement that justifies a Value Rule
  whose unit differs from the generated unit, or that corrected a migrated
  rule. Recorded as a comment above the entry, since the format rejects
  any key it does not define.
- **Scope:** every differing or corrected entry; an entry that only adds a
  unit the generated declaration lacks carries none.
- **Relationships:** documents a Value Rule; a rule the manual confirms as
  already generated correctly is dropped, not annotated.

- **Name:** Corpus Gap
- **Definition:** A built-in an analysis meets that the generated
  declarations do not carry: a class whose methods the extraction does not
  emit, or a function newer or older than the upstream release.
- **Scope:** excluded from the set; recorded as an extraction task.
- **Relationships:** resolved in the Extraction Pipeline, never by a Value
  Rule.

## 3. Contracts & Flow

**Data Contracts**
- **With the generated declarations:** every subject the set states has a
  generated entry; no default-branch unit equals the generated unit of the
  same subject.
- **With cobraphp-core:** the consumer mounts the set as one unmapped
  document set; the set names no category or color and needs no
  vocabulary. Its provenance is manual, so under the consumer's precedence
  its units outrank the generated ones whatever the mount order.

**Internal Processing Flow**
1. Classify — compare each migrated rule with the generated entry: no
   generated unit, differing unit, guarded branch, or Corpus Gap.
2. Review — check every differing or type-widened rule against the PHP
   manual: keep it with a Review Reason, correct it with a Review Reason,
   or drop it when the manual confirms the generated unit. A Corpus Gap
   becomes an extraction task in `todo.md`.
3. Emit — write the provenance and one document per PHP manual area,
   subjects sorted, guarded branches before the default.
4. Verify — the repository test loads the set beside the declarations and
   asserts provenance, existence, shape, and non-repetition.

## 4. Scenarios

- **Typical:** `strlen` has a signature and no flow annotation. The set
  states `returns: num` with the first argument flowing to the result; the
  consumer's result is a typed unknown instead of an untyped one.
- **Boundary:** `print_r` returns its rendering only when the second
  argument is true. A guarded entry states that branch; the default
  branch states a boolean result with no flow.
- **Interaction:** `mysqli::query` is stated in no document because the
  generated declarations carry no `mysqli` methods. The subject is a
  Corpus Gap; an extraction task, not this set, owns it.

Software structure: [design-value-rules.md](design-value-rules.md).
