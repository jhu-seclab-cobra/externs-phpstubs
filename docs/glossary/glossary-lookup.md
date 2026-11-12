# Glossary — Lookup

Builtin lookup: the vocabulary every shipped set is translated into, the merge of the shipped and consumer sets, and the facts a lookup answers.

---

## Merge

### Canonical Vocabulary
- **Definition:** This library's own Vocabulary of vulnerability types and source kinds, with the Policy over them, into which a Vocabulary Mapping this library ships translates every shipped Document Set that names them differently, so a consumer sees only these names.
- **Source:** `VulnType.kt` `VulnType`; `SourceKind.kt` `SourceKind`; `docs/concept-lookup.md` Core Concepts

### Set Merge
- **Definition:** The immutable result of folding mounted Document Sets into the Model in force for each Matching Subject, Condition and replacement unit, with manual Models preferred over generated Models and later mounts preferred at equal rank.
- **Example:** Two unconditional Models for `strlen`, generated and manual, asserting different Value units → the manual Value unit is in force.
- **Source:** `SetMerge.kt` `SetMerge`; `docs/spec-merge.md`

## Facts

### Fact
- **Definition:** One element of one assertion unit of an entry in force, carrying the Matching Subject it belongs to and the Condition it holds under: a source, sink, sanitizer, flow, returns, characters or throws assertion.
- **Example:** `mysqli::query` → the sink Fact at `argument(0)` with Vulnerability type `sqli`.
- **Source:** `Fact.kt` `Fact`, `SourceFact`, `SinkFact`, `SanitizerFact`, `FlowFact`, `ReturnsFact`, `CharactersFact`, `ThrowsFact`

## Libraries

### Library Set
- **Definition:** A generated Document Set containing a Composer package's Signatures and Facts in the Canonical Vocabulary, selectable by its package name.
- **Example:** `laravel/framework` → the generated declarations and Facts mounted by `PhpStubs.withLibraries`.
- **Source:** `LibrarySet.kt` `LibrarySet`; `PhpStubs.kt` `withLibraries`; `docs/design-taint-libraries.md` LibrarySet
