# PHP Stubs — Merge Design

Software structure of the mount and merge machinery behind
`BuiltinLookup`: how each document set becomes a `Mount`, how a `MountSequence`
threads the vocabulary and classifies failures, and how `SetMerge` folds the
mounts into records. Every type here is internal; the public surface is
[design-lookup.md](design-lookup.md). Fold algorithm:
[spec-merge.md](spec-merge.md). mount order and generated-set rules:
[design.md](design.md).

## Design Overview

- **Classes:** `Mount` (internal data class), `MountSequence` (internal
  class), `SetMerge` (internal class), `OverrideUnit` (internal enum:
  `SIGNATURE`, `VALUE`, `SOURCES`, `SINKS`, `SANITIZERS`, `THROWS`)
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `Document`, `ResourceOpener`, `VocabularyMapping`,
  `ModelEntry`, `PolicyRow`, `Vocabulary`, `TaintPolicy`, `Precedence`,
  `Verification`, `DocumentSetException`
- **Relationships:** `MountSequence` produces `Mount`s in position order;
  `SetMerge.of` consumes them and builds one `BuiltinRecord` per subject.
  `PhpStubs` owns one mount list and one `SetMerge`.
- **Exceptions:** `StubIndexNotFoundException`, `StubIndexInvalidException`
  ([design.md](design.md) Exception / Error Types).
- **Dependency roles:** Builder: `MountSequence`. Data holder: `Mount`.
  Aggregate: `SetMerge`.

## Class / Type Specifications

### Mount (internal data class)

**Responsibility:** One set as mounted: its position in mount order, its
verification, the vocabulary and policy rows it declares, and its entries,
each paired with the extension its document path yields (`.yaml` removed,
trailing `_<digits>` removed) for every mount validated as generated and `null` for other mounts.

**State/Fields:** `position: Int`, `verification: Verification`,
`vocabulary: Vocabulary`, `policy: List<PolicyRow>`,
`entries: List<Pair<ModelEntry, String?>>`.

### MountSequence (internal class)

**Responsibility:** Builds mounts in order, decoding each set through
`DocumentSetLoader.load(opener, accumulated vocabulary, mapping)` and
classifying failures. `mount(root, open, mapping, fallback, generated)`:
`fallback` is the verification of a set without `provenance.yaml` (`MANUAL`
for consumer sets, `null` for bundled sets, where absence is
`StubIndexInvalidException`); `generated = true` applies the generated-set
rules and derives PHP extensions. A failure naming a path the opener
returned `null` for is `StubIndexNotFoundException`; any other is
`StubIndexInvalidException` with the cause attached.

### SetMerge (internal class)

**Responsibility:** The fold of [spec-merge.md](spec-merge.md) and the
records built from its result. Built once per set sequence, immutable.

**State/Fields:** `vocabulary`, `policy`, one insertion-ordered map from a concrete `ModelSubject` subtype to its `BuiltinRecord` per declaration kind in mount order of each subject's first mounted entry,
whatever its rank, and the seven fact lists in record order. The class map
also holds the alias keys that the alias-key step of
[spec-merge.md](spec-merge.md#steps) adds.

**Construction:** `SetMerge.of(mounts: List<Mount>, precedence: Precedence = Precedence.DEFAULT)` returns the immutable merge. Conditional Signatures raise `StubIndexInvalidException`; alias collisions raise the same error. Record assembly, ordering and alias keys implement [Set Merge](spec-merge.md); canonical tries are populated only from final records with an effective Signature.

## Validation Rules

- Every mount's position equals its index in the sequence.
- A bundled set without `provenance.yaml` never mounts; a consumer set
  without one mounts as `MANUAL`.
- The generated-set rules and PHP extension derivation apply independently to every mount flagged generated, including selected Library Sets.
- `SetMerge.records` holds every declaration subject any mount states, and
  each subject appears in exactly one kind map; class-map key relations
  follow [model-lookup.md](model-lookup.md#relations).

## Exception / Error Types

`MountSequence` classifies load failures as [resource errors](design.md#exception--error-types); `SetMerge.of` propagates those errors.
