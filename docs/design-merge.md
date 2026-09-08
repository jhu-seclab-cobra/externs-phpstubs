# PHP Stubs — Merge Design

Software structure of the mount and merge machinery behind the Built-in
Lookup: how each document set becomes a `Mount`, how a `MountSequence`
threads the vocabulary and classifies failures, and how `Merge` folds the
mounts into records. Every type here is internal; the public surface is
[design-lookup.md](design-lookup.md). Fold algorithm:
[spec-merge.md](spec-merge.md). Merge Order and corpus rules:
[design.md](design.md).

## Design Overview

- **Classes:** `Mount` (internal data class), `MountSequence` (internal
  class), `Merge` (internal class), `OverrideUnit` (internal enum:
  `SIGNATURE`, `VALUE`, `SOURCES`, `SINKS`, `SANITIZERS`)
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `Document`, `ResourceOpener`, `CategoryMapping`,
  `ModelEntry`, `PolicyRow`, `Vocabulary`, `TaintPolicy`, `Precedence`,
  `Verification`, `DocumentSetException`
- **Relationships:** `MountSequence` produces `Mount`s in position order;
  `Merge.of` consumes them and builds one `BuiltinRecord` per subject.
  `PhpStubs` owns one mount list and one `Merge`.
- **Dependency roles:** Builder: `MountSequence`. Data holder: `Mount`.
  Aggregate: `Merge`.

## Class / Type Specifications

### Mount (internal data class)

**Responsibility:** One set as mounted: its position in Merge Order, its
verification, the vocabulary and policy rows it declares, and its entries,
each paired with the extension its document path yields (`.yaml` removed,
trailing `_<digits>` removed) for the generated set and `null` for every
other set.

**State/Fields:** `position: Int`, `verification: Verification`,
`vocabulary: Vocabulary`, `policy: List<PolicyRow>`,
`entries: List<Pair<ModelEntry, String?>>`.

### MountSequence (internal class)

**Responsibility:** Builds mounts in order, decoding each set through
`DocumentSetLoader.load(opener, accumulated vocabulary, mapping)` and
classifying failures. `mount(label, open, mapping, fallback, corpus)`:
`fallback` is the verification of a set without `provenance.yaml` (`MANUAL`
for extension sets, `null` for bundled sets, where absence is
`StubIndexInvalidException`); `corpus = true` applies the generated set's
corpus rules and derives extensions. A failure naming a path the opener
returned `null` for is `StubIndexNotFoundException`; any other is
`StubIndexInvalidException` with the cause attached.

### Merge (internal class)

**Responsibility:** The fold of [spec-merge.md](spec-merge.md) and the
records built from its result. Built once per set sequence, immutable.

**State/Fields:** `vocabulary`, `policy`, one `LinkedHashMap<Subject, BuiltinRecord>`
per declaration kind in first-statement order, and the five fact lists in
record order.

**Construction (`Merge.of(mounts: List<Mount>)`):** for each mount in
position order and each entry: key = (subject, condition); per unit the
entry declares, the statement in force is replaced when the new statement's
verification ranks at least equal under `Precedence.DEFAULT` (equal rank,
later position wins; lower rank never replaces). The extension of a record
is the extension of the statement in force for its signature unit. A
conditional entry declaring a signature is `StubIndexInvalidException`.

**Record assembly:** per subject, the signature is the unconditional
signature statement or `null`; the facts are every element of every
statement in force under every condition of that subject, each tagged with
its condition. Statement order within a subject is condition
first-statement order; element order is document order.

## Validation Rules

- Every mount's position equals its index in the sequence.
- A bundled set without `provenance.yaml` never mounts; an extension set
  without one mounts as `MANUAL`.
- The corpus rules and extension derivation apply to exactly the mount
  flagged as the generated corpus.
- `Merge.records` holds every subject any mount states, and each subject
  appears in exactly one kind map.
