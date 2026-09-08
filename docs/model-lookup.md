# PHP Stubs — Lookup Domain Model

Domain semantics of the Built-in Lookup: the sets this library merges, the
vocabulary they end in, and the records a consumer reads by PHP name. The
format entities — Model, Matching Subject, Signature, Section, Origin
Color, Danger Category — and the merge entities — Model Index, Section
Precedence, Guard Context, Effective Statement — are the library's:
`extern/commons-phpmodels/docs/model.md`, `model-index.md`.

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
- **Merge Order** — The fixed Mount Order of the Bundled Sets: generated
  declarations, value rules, Canonical Vocabulary, taint (mapped), taint
  rules (mapped). Fixed by this library; a consumer neither reorders nor
  omits a set.
- **Extension Set** — A document set a consumer supplies beside the
  bundled ones: a directory or classpath root holding a manifest. Mounted
  after every Bundled Set, in the order supplied; a set without provenance
  mounts as manual. Its names are Canonical Vocabulary names or its own
  vocabulary additions; it carries no mapping.
- **Extension** — The PHP extension a declaration belongs to, derived from
  the generated document's placement (`mysqli`, `standard`, `keyword`,
  `scalar`, ...). Data tier: read from placement, never a constant in code.
  A subject declared only by a non-generated set has no Extension.
- **Built-in Record** — One subject that exists in the Model Index
  (default-branch signature present): its PHP spelling, its Extension, its
  signature, and its Effective Statement under a Guard Context the reader
  supplies — unknown context when the reader supplies none. Existence
  condition: the subject exists after the merge. Identity is the subject.
  One record kind per declaration kind: function, method, class, constant,
  class constant, property.
- **Fact** — One element of a record's guarded sections, carrying its owner
  record: a *sink* (port, danger category), a *source* (produced colors,
  site, key patterns), a *sanitizer* (neutralized categories), a *flow*
  (one propagation pair). Read from the default-context Effective
  Statement, so a fact from a guarded branch is present — the sound union.
- **Built-in Lookup** — The two reading modes over one Model Index:
  *exact* — one PHP spelling (`substr`, `mysqli::query`, `PDO`,
  `PHP_INT_MAX`, `PDO::ATTR_ERRMODE`), or owner and name apart, to at most
  one record; *enumeration* — every record of one declaration kind, or
  every Fact of one fact kind, for the consumer to filter. No third mode:
  a match looser than exact is the consumer's filter over an enumeration.

## Relations

| From | To | Relation | Cardinality | Meaning |
|------|----|----------|-------------|---------|
| Built-in Lookup | Model Index | reads | 1:1 | One index per lookup; bundled or bundled plus extensions |
| Model Index | Bundled Set | merges | 1:4 | In Merge Order, under the default Precedence |
| Model Index | Extension Set | merges | 1:N | After the bundled sets, in supplied order |
| Psalm Mapping | Bundled Set | translates | 1:2 | The taint set and the taint rules set |
| Canonical Vocabulary | Fact | names | 1:N | Every category and color a fact carries |
| Built-in Record | Matching Subject | identifies | 1:1 | PHP spelling folded per kind |
| Built-in Record | Extension | belongs to | N:0..1 | From the generated set's document placement |
| Built-in Record | Fact | owns | 1:N | Every fact names the record it was read from |
| Built-in Record | Effective Statement | reads | 1:N | One statement per Guard Context supplied |

## State Model

### Lookup

| State | Trigger | Target |
|-------|---------|-------|
| Unread | first lookup on the bundled index | merged once, frozen, shared by every later lookup |
| Frozen | exact lookup, subject exists | one record |
| Frozen | exact lookup, subject absent | no record; not a failure |
| Frozen | exact lookup, name not a PHP spelling | argument error |
| Frozen | enumeration | every record or fact of the kind, in registry load order |
| Frozen | extension sets supplied | a second index: bundled sets then extensions; the bundled index unchanged |

### Reading a Record

| State | Trigger | Target |
|-------|---------|-------|
| Record | no Guard Context | Effective Statement under the unknown context: sound union |
| Record | Guard Context supplied | Effective Statement for that context |
| Record | signature read | the default-branch signature; never guard-dependent |

## Invariants

- Every Built-in Record has a signature: existence is the default-branch
  signature, and the generated set declares one on every entry.
- The Canonical Vocabulary is mounted before the mapped sets and before
  any Extension Set; every mapping target is one of its names.
- No psalm name survives the merge: every kind of the two psalm-named sets
  is mapped or discarded, and a discarded-only element is dropped.
- Merge Order is fixed and complete: the four bundled sets, once each, in
  the stated order, under the default Precedence.
- An Extension Set never precedes a Bundled Set and never changes the
  bundled index; two lookups built from the same sets in the same order
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

- **With commons-phpmodels.** The merge, the precedence, the candidate set,
  and the combination are the library's; this library fixes only which sets
  mount in which order under which mapping.
- **With the taint sets.** A category or color a psalm-named set introduces
  is declared in that set's vocabulary document and given a mapping row;
  an unmapped kind fails the merge.
- **With consumers.** A consumer names a built-in by its PHP spelling and
  reads a record; it holds no set, mapping, vocabulary, or precedence.
  Guard Arguments are the consumer's conversion; the record answers.
- **With extension producers.** An Extension Set is written in the
  Canonical Vocabulary (plus its own additions) and mounts after the
  bundled sets, so its manual declarations replace generated ones and tie
  with bundled manual ones by later Mount Order.

Rationale: [concept-lookup.md](concept-lookup.md). Software structure:
[design-lookup.md](design-lookup.md).
