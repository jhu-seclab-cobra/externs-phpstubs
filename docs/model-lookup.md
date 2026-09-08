# PHP Stubs — Lookup Domain Model

Domain semantics of the Built-in Lookup: the sets this library merges, the
vocabulary they end in, the merge, and the records a consumer reads by PHP
name. The format entities — Model, Matching Subject, Signature, Section,
Override Unit, Condition, Conditional Entry, Unconditional Entry, Origin
Color, Danger Category, Document Set, Set Provenance, Precedence — are the
format library's: `extern/commons-phpmodels/docs/model.md`,
`model-conditions.md`, `model-sets.md`.

## Entities

- **Bundled Set** — One of the four document sets this library ships:
  the generated declaration set (the Stub Registry as a set), the value
  rules set, the taint set, the taint rules set. Identity is its resource
  root. Each carries a Set Provenance; generated for the first and third,
  manual for the others.
- **Canonical Vocabulary** — The danger categories and origin colors every
  record speaks: twelve categories (`sqli`, `cmdi`, `codei`, `xss`,
  `headeri`, `ssrf`, `pathtrav`, `fileinc`, `deser`, `callablei`, `ldapi`,
  `xpathi`) and two colors (`user-input`, `external-input`), with the policy
  enabling every category under both colors. A hand-written set of this
  library, mounted before any set that names a category or color.
  Existence condition: declared in the vocabulary document; adding a name
  is a data-file edit.
- **Psalm Mapping** — This library's total function from the psalm kinds
  the taint set and the taint rules set use to Canonical Vocabulary names,
  or to *discarded* for a kind with no canonical meaning (`has_quotes`,
  `cookie`, `user_secret`, `system_secret`). Applied at the merge to both
  sets; a consumer never sees a psalm name.
- **Merge Order** — The fixed mount order of the Bundled Sets: generated
  declarations, value rules, Canonical Vocabulary, taint (mapped), taint
  rules (mapped). Fixed by this library; a consumer neither reorders nor
  omits a set.
- **Extension Set** — A document set a consumer supplies beside the
  bundled ones: a directory or classpath root holding a manifest. Mounted
  after every Bundled Set, in the order supplied; a set without provenance
  mounts as manual. Its names are Canonical Vocabulary names or its own
  vocabulary additions; it carries no mapping.
- **Statement** — One entry's content for one Override Unit, keyed by
  (subject, condition, unit), together with the Set Provenance of the set
  that stated it and that set's position in Merge Order.
- **Merge** — The map from every (subject, condition, unit) key stated by
  any mounted set to the one Statement in force for it. Built once per set
  sequence and frozen. Two Statements with the same key compete; a
  Statement with a different condition never competes.
- **Extension** — The PHP extension a declaration belongs to, derived from
  the generated document's placement (`mysqli`, `standard`, `keyword`,
  `scalar`, ...). Data tier: read from placement, never a constant in code.
  A subject declared only by a non-generated set has no Extension.
- **Built-in Record** — One subject the Merge holds any Statement for:
  its PHP spelling, its Extension, its signature when an unconditional
  signature Statement is in force, and its Facts. Existence condition: the
  subject is keyed after the merge. Identity is the subject. One record
  kind per subject kind: function, method, class, constant, class
  constant, property, predefined variable.
- **Fact** — One element of a record's assertion Statements, carrying its
  owner record and the Condition of the entry it came from, or none: a
  *sink* (port, danger category), a *source* (produced colors, site, key
  patterns), a *sanitizer* (neutralized categories), a *flow* (one
  propagation pair), a *returns* (the classification). Every Fact of every
  entry is present; the record ranks none of them against a call.
- **Built-in Lookup** — The two reading modes over one Merge:
  *exact* — one PHP spelling (`substr`, `mysqli::query`, `PDO`,
  `PHP_INT_MAX`, `PDO::ATTR_ERRMODE`), or owner and name apart, to at most
  one record; *enumeration* — every record of one declaration kind, or
  every Fact of one fact kind, for the consumer to filter. No third mode:
  a match looser than exact is the consumer's filter over an enumeration.

## Relations

| From | To | Relation | Cardinality | Meaning |
|------|----|----------|-------------|---------|
| Built-in Lookup | Merge | reads | 1:1 | One merge per lookup; bundled or bundled plus extensions |
| Merge | Bundled Set | folds | 1:4 | In Merge Order, under the default Precedence |
| Merge | Extension Set | folds | 1:N | After the bundled sets, in supplied order |
| Merge | Statement | holds | 1:N | Exactly one per (subject, condition, unit) key stated by any set |
| Psalm Mapping | Bundled Set | translates | 1:2 | The taint set and the taint rules set |
| Canonical Vocabulary | Fact | names | 1:N | Every category and color a fact carries |
| Built-in Record | Matching Subject | identifies | 1:1 | PHP spelling folded per kind |
| Built-in Record | Extension | belongs to | N:0..1 | From the generated set's document placement |
| Built-in Record | Fact | owns | 1:N | Every fact names the record it was read from |
| Fact | Condition | carries | N:0..1 | The condition of the entry that stated it |

## State Model

### Statement in Force

Two Statements with the same (subject, condition, unit) key:

| Comparison | In force |
|------------|----------|
| Set Provenance ranks differ | The higher rank (manual over generated) |
| Ranks equal, Merge Order positions differ | The later position |
| Same set, same key | Load failure (the set's own duplicate rule) |

### Lookup

| State | Trigger | Target |
|-------|---------|-------|
| Unread | first lookup on the bundled merge | folded once, frozen, shared by every later lookup |
| Frozen | exact lookup, subject exists | one record |
| Frozen | exact lookup, subject absent | no record; not a failure |
| Frozen | exact lookup, name not a PHP spelling | argument error |
| Frozen | enumeration | every record or fact of the kind, in registry load order |
| Frozen | extension sets supplied | a second merge: bundled sets then extensions; the bundled merge unchanged |

## Invariants

- A Built-in Record holds a signature or at least one Fact; a declared
  built-in is a record whose signature is in force, and the generated set
  declares one on every entry. A predefined-variable record never holds a
  signature.
- The signature Statement is unconditional: a conditional entry that
  declares a signature is a load failure.
- The Canonical Vocabulary is mounted before the mapped sets and before
  any Extension Set; every mapping target is one of its names.
- No psalm name survives the merge: every kind of the two psalm-named sets
  is mapped or discarded, and a discarded-only element is dropped.
- Merge Order is fixed and complete: the four bundled sets, once each, in
  the stated order, under the default Precedence.
- A Statement is replaced whole per key, never merged with the one it
  replaces; a later set that omits a unit leaves the earlier Statement in
  force for that unit.
- Conditions partition the Statements of one subject and unit: a
  conditional Statement never replaces an unconditional one, and the
  reverse never happens.
- An Extension Set never precedes a Bundled Set and never changes the
  bundled merge; two lookups built from the same sets in the same order
  give equal records.
- Exact lookup is exact: the spelling is folded per kind by the format
  library and compared whole; no suffix, prefix, or case-insensitive match
  exists in the lookup.
- Enumeration order is registry load order, so a consumer's "first match"
  is deterministic.
- A Fact always names its owner; a fact never exists apart from a record.
- The value rules set corrects only subjects the generated set declares,
  and never repeats a value-semantics unit the generated set already states.

## Cross-Structure Contracts

- **With commons-phpmodels.** Decoding, validation, the (subject,
  condition, unit) key, the Precedence over Set Provenance, and the
  condition match operation are the format library's; this library fixes
  which sets mount in which order under which mapping and applies the
  Precedence.
- **With the taint sets.** A category or color a psalm-named set introduces
  is declared in that set's vocabulary document and given a mapping row;
  an unmapped kind fails the merge.
- **With consumers.** A consumer names a built-in by its PHP spelling and
  reads a record; it holds no set, mapping, vocabulary, or precedence.
  Call Arguments are the consumer's conversion; the consumer matches each
  Fact's Condition and applies its own rule to an undecidable outcome.
- **With extension producers.** An Extension Set is written in the
  Canonical Vocabulary (plus its own additions) and mounts after the
  bundled sets, so its manual declarations replace generated ones and
  outrank bundled manual ones by later Merge Order.

Rationale: [concept-lookup.md](concept-lookup.md). Software structure:
[design-lookup.md](design-lookup.md).
