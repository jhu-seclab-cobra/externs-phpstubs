# PHP Stubs — Lookup Domain Model

Domain semantics of `BuiltinLookup`: the sets this library merges, the
vocabulary they end in, the Set Merge, and the records a consumer reads by PHP
name. The format entities — Model, Matching Subject, Signature, Section,
replacement unit, Condition, conditional Model, unconditional Model, Source kind, Vulnerability type, Document Set, Set Provenance, Precedence — are the
format library's: [format model](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/d356ff45becb5983fc66ac544a00df6618ac224b/docs/model.md),
[model-conditions.md](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/d356ff45becb5983fc66ac544a00df6618ac224b/docs/model-conditions.md), [model-sets.md](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/d356ff45becb5983fc66ac544a00df6618ac224b/docs/model-sets.md).

## Entities

- **bundled Document Set** — One of the five document sets this library ships:
  the generated set, the value rules set, the Canonical
  Vocabulary set, the taint set, the taint rules set. Identity is its
  resource root. Each carries a Set Provenance; generated for the
  declaration set and the taint set, manual for the others.
- **Canonical Vocabulary** — The vulnerability types and source kinds every
  record speaks: sixteen Vulnerability type names (`sqli`, `cmdi`, `codei`, `xss`,
  `headeri`, `ssrf`, `pathtrav`, `fileinc`, `deser`, `callablei`, `ldapi`,
  `xpathi`, `schemei`, `openredirect`, `nosqli`, `templatei`) and three Source kind names (`user-input`, `external-input`, `server-path`).
  The first two enable every Vulnerability type; `server-path` enables every type
  except `schemei`. Only `schemei` declares a Tokenizer language; its
  transitions recognize the leading position of a URL attribute value in HTML. A hand-written
  set of this library, mounted before any set that names a vulnerability
  type or source kind.
  Existence condition: declared in the vocabulary document; adding a name
  is a data-file edit.
- **Psalm Mapping** — This library's total function from the psalm kinds
  the taint set and the taint rules set use to Canonical Vocabulary names,
  or to *discarded* for a kind with no canonical meaning (`has_quotes`,
  `cookie`, `user_secret`, `system_secret`). Applied at the merge to both
  sets; a consumer never sees a psalm name.
- **mount order** — The position order of every mounted set: the bundled Document Sets first, in a fixed order (generated declarations, value rules,
  Canonical Vocabulary, taint (mapped), taint rules (mapped)), then the
  consumer Document Sets in the order supplied. The bundled prefix is fixed by this
  library; a consumer neither reorders nor omits a bundled Document Set.
- **consumer Document Set** — A document set a consumer supplies beside the
  bundled ones: a directory or classpath root holding a manifest. Mounted
  after every bundled Document Set, in the order supplied; a set without provenance
  mounts as manual. Its names are Canonical Vocabulary names or its own
  vocabulary additions; it carries no mapping.
- **Set Merge** — The map from every (subject, condition, unit) key stated by
  any mounted set to the entry in force for it, with the Set Provenance
  rank and mount order position of the set that stated it. Built once per
  set sequence and never changed. Two entries stating the same key
  compete; an entry with a different condition never competes.
- **PHP extension** — The PHP extension a declaration belongs to, derived from
  the generated document's placement (`mysqli`, `standard`, `keyword`,
  `scalar`, ...). A record’s PHP extension comes from the mount supplying its effective Signature; it is absent when that mount does not derive extension metadata.
- **`BuiltinRecord`** — One subject the Set Merge holds any entry in force for:
  its PHP spelling, its PHP extension, its signature when an unconditional
  signature is in force, and its Facts. Existence condition: the
  subject is keyed after the merge. Identity is the subject. One record
  kind per subject kind: function, method, class, constant, class
  constant, property, predefined variable.
- **Fact** — One element of an assertion unit of a record's entries in force, carrying its
  owner’s Matching Subject and the Condition of the entry it came from, or none: a
  *sink* (port, vulnerability type), a *source* (produced source kinds,
  site, key patterns), a *sanitizer* (neutralized vulnerability types), a *flow* (one
  propagation pair), a *characters* (the bytes the result may hold, the
  whole section in one Fact), a *returns* (the return kind), a *throws* (the
  exception classes the subject's own implementation may throw, the whole
  section in one Fact, so the empty set states it throws none). Every Fact of every
  entry is present; the record ranks none of them against a call.
- **`BuiltinLookup`** — The reading modes over one Set Merge:
  *exact* — one PHP spelling (`substr`, `mysqli::query`, `PDO`,
  `PHP_INT_MAX`, `PDO::ATTR_ERRMODE`), or owner and name apart, to at most
  one record; *enumeration* — every record of one declaration kind, or
  every Fact of one Fact kind, for the consumer to filter. A third mode matches an original literal/gap name pattern against canonical function/class declarations whose effective record has a signature; class-alias keys are not additional matching declarations. Existence consumes the first match; complete lookup consumes every match. Each immutable merge owns its own name dictionary.

## Relations

| From | To | Relation | Cardinality | Meaning |
|------|----|----------|-------------|---------|
| `BuiltinLookup` | Set Merge | reads | 1:1 | One Set Merge per lookup; bundled or bundled plus consumer sets |
| Set Merge | bundled Document Set | folds | 1:5 | In mount order, under the default Precedence |
| Set Merge | consumer Document Set | folds | 1:N | After the bundled sets, in supplied order |
| Set Merge | entry in force | holds | 1:N | Exactly one per (subject, condition, unit) key stated by any set |
| class-alias key | `BuiltinRecord` | reads | N:1 | Each class-alias key reads the record whose class signature states it; the record retains its declaration subject |
| Psalm Mapping | bundled Document Set | translates | 1:2 | The taint set and the taint rules set |
| Canonical Vocabulary | Fact | names | 1:N | Every vulnerability type and source kind a Fact carries |
| `BuiltinRecord` | Matching Subject | identifies | 1:1 | PHP spelling folded per kind |
| `BuiltinRecord` | PHP extension | belongs to | N:0..1 | From the generated set's document placement |
| `BuiltinRecord` | Fact | owns | 1:0..N | Each Fact carries its owner’s Matching Subject |
| Fact | Condition | carries | N:0..1 | The condition of the entry that stated it |

## State Model

### Entry in Force

Two entries stating the same (subject, condition, unit) key:

| Comparison | In force |
|------------|----------|
| Set Provenance ranks differ | The higher rank (manual over generated) |
| Ranks equal, mount order positions differ | The later position |
| Same document, same key | Load failure (the format's per-document duplicate rule) |
| Same set, different documents, same key | The later document (the generated set: load failure, generated-set rule) |

### Lookup

| State | Trigger | Target |
|-------|---------|-------|
| Unread | first lookup on the bundled merge | Built: folded once, shared by every later lookup |
| Built | `clazz(name)`, declared name or class-alias key present | one record |
| Built | `record(subject)` or another exact lookup, declaration subject present | one record |
| Built | exact lookup, key absent from the accessor's own map | no record; not a failure |
| Built | exact lookup, name not a PHP spelling | argument error |
| Built | enumeration | every record or Fact of the kind, in enumeration order (Invariants) |
| Built | consumer sets supplied | a second merge: bundled sets then consumer sets; the bundled merge unchanged |

## Invariants

- A `BuiltinRecord` holds a signature or at least one Fact; a declared
  builtin is a record whose signature is in force, and the generated set
  declares one on every entry. A predefined-variable record never holds a
  signature.
- The signature in force is unconditional: a conditional entry that
  declares a signature is a load failure.
- The Canonical Vocabulary is mounted before the mapped sets and before
  any consumer Document Set; every mapping target is one of its names.
- No psalm name survives the merge: every kind of the two psalm-named sets
  is mapped or discarded, and a discarded-only element is dropped.
- The default bundled prefix has five Document Sets, once each, in the stated order; selected Library Sets and consumer Document Sets follow it. Each selected Library Set receives generated-set validation.
- The entry in force is replaced whole per key, never combined with the
  one it replaces; a later set that omits a unit leaves the earlier entry in
  force for that unit.
- Different Conditions identify distinct keys for one Matching Subject and replacement unit: a
  conditional Model never replaces an unconditional Model, and the reverse never happens; different Conditions may both hold at one call.
- A consumer Document Set never precedes a bundled Document Set and never changes the
  bundled merge; two lookups built from the same sets in the same order
  give equal records.
- Exact lookup is exact: the spelling is folded per kind by the format
  library and compared whole; the exact accessor does not interpret a name pattern. Class-alias keys are the relation in
  [Relations](#relations).
- Enumeration order is deterministic, so a consumer's "first match" is:
  records in mount order of each subject's first mounted entry, whatever
  its rank; Facts in record order, then conditions in mount order of their
  first entry, then replacement unit order, then document order.
- A Fact always names its owner; a Fact never exists apart from a record.
- The value rules set corrects only subjects the generated set declares,
  and never repeats a value unit the generated set already states.

## Cross-Structure Contracts

- **With commons-phpmodels.** Decoding, validation, the (subject,
  condition, unit) key, the Precedence over Set Provenance, and the
  condition match operation are the format library's; this library fixes
  which sets mount in which order under which mapping and applies the
  Precedence.
- **With the taint sets.** A vulnerability type or source kind a psalm-named set introduces
  is declared in that set's vocabulary document and given a mapping row;
  an unmapped kind fails the merge.
- **With consumers.** A consumer names a builtin by its PHP spelling and
  reads a record; it holds no merge state: no loaded set, mapping,
  vocabulary, or precedence.
  call arguments are the consumer's conversion; the consumer matches each
  Fact's Condition and applies its own rule to an undecidable outcome.
- **With consumer sets.** A consumer Document Set is written in the
  Canonical Vocabulary (plus its own additions) and mounts after the
  bundled sets, so its manual declarations replace generated ones and
  outrank bundled manual ones by later mount order.

Rationale: [concept-lookup.md](concept-lookup.md). Software structure:
[design-lookup.md](design-lookup.md).
