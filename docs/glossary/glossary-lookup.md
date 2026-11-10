# Glossary — Lookup

Builtin lookup: the vocabulary every shipped set is translated into, the merge of the shipped and consumer sets, and the facts a lookup answers.

---

## Merge

### Canonical Vocabulary
- **Definition:** This library's own Vocabulary of vulnerability types and source kinds, with the Policy over them, into which a Vocabulary Mapping this library ships translates every shipped Document Set that names them differently, so a consumer sees only these names.
- **Source:** `VulnType.kt` `VulnType`; `SourceKind.kt` `SourceKind`; `docs/concept-lookup.md` Core Concepts
- **Reference:** none

### Set Merge
- **Definition:** The folding of the mounted document sets, in mount order, into the entry in force per Matching Subject, Condition and override unit, in which an entry of a manual set outranks a generated one and, among equals, the later mounted set wins.
- **Source:** `SetMerge.kt` `SetMerge`; `docs/spec-merge.md`
- **Reference:** none

## Facts

### Fact
- **Definition:** One element of one assertion unit of an entry in force, carrying the Matching Subject it belongs to and the Condition it holds under: a source, sink, sanitizer, flow, returns, characters or throws fact.
- **Source:** `Fact.kt` `Fact`, `SourceFact`, `SinkFact`, `SanitizerFact`, `FlowFact`, `ReturnsFact`, `CharactersFact`, `ThrowsFact`
- **Reference:** none

## Libraries

### Library Set
- **Definition:** A generated Document Set containing a Composer package's Signatures and Facts in the Canonical Vocabulary, selectable by its package name.
- **Example:** `laravel/framework` → the generated declarations and Facts mounted by `PhpStubs.withLibraries`.
- **Source:** `LibrarySet.kt` `LibrarySet`; `PhpStubs.kt` `withLibraries`; `docs/design-taint-libraries.md` LibrarySet
