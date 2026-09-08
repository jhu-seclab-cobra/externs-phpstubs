# PHP Stubs — Lookup Concept

Extends [concept.md](concept.md) with what this library does beyond
shipping data: merging its sets into one body of facts and answering
lookups by PHP name. Model Entry, Subject, Stub Registry, Generated Layer,
and Extension Provenance are defined there; Model, Section, Condition,
Document Set, Set Provenance, and Verification in commons-phpmodels
`docs/concept.md` and `concept-provenance.md`.

## 1. Context

**Problem Statement**
Before this concern, a consumer of this library received four document
sets and a registry and had to merge them itself: choose a mount order,
declare its own vocabulary, write a mapping from psalm's names, rank sets
by provenance. Every consumer repeated that work, and this library could
not check that its own sets merge. A consumer that wants to know what
`substr` does, or which built-ins are SQL injection sinks, should ask by
name and read the answer.

**System Role**
This concern is the library's read surface: it fixes the vocabulary every
fact is stated in, merges the shipped sets once, and answers by PHP name.
It adds no fact of its own and evaluates no condition: a fact is returned
with its condition attached, and the consumer, which alone knows the call,
decides.

**Data Flow**
- **Inputs:** the Stub Registry, the value rules set, the canonical
  vocabulary and policy, the taint set and the taint rules set with the
  one mapping that translates them; optionally a consumer's extension sets.
- **Outputs:** one Built-in Record per PHP name; the returns, flows,
  sources, sinks, and sanitizers of every record enumerable by kind.
- **Connections:** registry + sets → Merge → Built-in Lookup → consumers.

**Scope Boundaries**
- **Owned:** the Canonical Vocabulary, the mapping onto it, the merge
  order and the merge itself (which set's statement is in force per
  subject, condition, and section), the exact lookup by PHP spelling, and
  enumeration by declaration kind and by fact kind. Any looser match is the
  consumer's filter over an enumeration, never a rule here.
- **Not Owned:** the format and its decoding (commons-phpmodels); deciding
  whether a fact's condition holds at a call, and computing a call's
  result (consumers).

## 2. Concepts

**Conceptual Diagram**
```
Stub Registry (generated set) ──┐
value-rules/ (manual) ──────────┤
canonical vocabulary + policy ──┤──► Merge (manual over generated, per subject / condition / section)
taint/ ──── mapping ────────────┤                       │
taint-rules/ ── same mapping ───┘                       ▼
consumer: PHP name ────────► Built-in Lookup ──► Built-in Record ──► signature, returns, flows, sources, sinks, sanitizers
consumer: declaration kind ─► Built-in Lookup ──► every record of that kind, filtered by the consumer
consumer: fact kind ────────► Built-in Lookup ──► every fact of that kind, each naming its record
```

**Core Concepts**

- **Name:** Canonical Vocabulary
- **Definition:** This library's own names for danger categories (SQL
  injection, command injection, ...) and origin colors (user input,
  external input), with the policy rows over them. The psalm-named sets
  are translated into it by one category mapping this library ships and
  applies at the merge; a consumer never sees psalm's names.
- **Scope:** every category and color any shipped set states.
- **Relationships:** context of the merge; the names every fact is in.

- **Name:** Merge
- **Definition:** Folding the sets, in this library's fixed order, into one
  statement per (subject, condition, section): a manual set's statement
  outranks a generated one; among equals the later mounted wins. Two
  entries for one subject with different conditions are two statements,
  both kept. Built once, lazily; internal.
- **Scope:** the Generated Layer, the value rules set, the Canonical
  Vocabulary, the taint set, the taint rules set, then extension sets.
- **Relationships:** consumes commons-phpmodels document sets; read by the
  Built-in Lookup.

- **Name:** Built-in Record
- **Definition:** What the Built-in Lookup answers for one PHP name: the
  extension, the signature, and the facts the merge holds for that subject
  — returns, flows, sources, sinks, sanitizers — each carrying the
  condition its entry declared, or none. The same facts are enumerable by
  kind, each naming the record it belongs to.
- **Scope:** one per subject with a signature; a name without one has no
  record.
- **Relationships:** read from the Merge; identified by its Subject.

- **Name:** Built-in Lookup
- **Definition:** The entry point consumers use. An exact lookup asks for
  a function, method, class, constant, class constant, or property by its
  PHP spelling — a member either as one `Owner::name` string or as owner
  and name apart — and is answered with its Built-in Record or nothing.
  An enumeration yields every record of one declaration kind, or every
  fact of one fact kind, for the consumer to filter by its own rule.
- **Scope:** exact lookup by name; enumeration by declaration kind and by
  fact kind. Extension sets give a second lookup beside the bundled one.
- **Relationships:** reads the Merge; answers consumer queries.

## 3. Contracts & Flow

**Data Contracts**
- **With commons-phpmodels:** each set is decoded and validated there; the
  merge here ranks by the set provenance each set declares.
- **With the document sets:** each set stays valid on its own; the
  repository test merges all of them and fails on an undeclared name, a
  conflicting redeclaration, or a mapping that omits a psalm kind.
- **With consumers:** a lookup takes a PHP spelling and answers a record
  or nothing; a name that is not a PHP identifier spelling is an argument
  error. Every fact is returned with its condition; the consumer matches
  the condition against the call's arguments with the format library's one
  matching operation and applies its own rule to an unknown outcome.
- **With extension sets:** a consumer that ships its own document set
  obtains a second lookup over the bundled sets plus its own, mounted
  after them, from a directory or classpath root. The set follows the
  document-set convention and names only the Canonical Vocabulary or its
  own additions; without a provenance document it ranks as manual.

**Internal Processing Flow**
1. Merge — decode each set in order, fold by rank then order, freeze.
2. Resolve — parse the lookup name into a Subject through the format
   library's creators, so folding is decided once.
3. Read — take the subject's statements; the record exposes each section's
   facts with their conditions.
4. Enumerate — walk every subject and yield the records of one declaration
   kind, or the facts of one fact kind, each with its record.

## 4. Scenarios

- **Typical:** `mysqli::query` asked by owner and name. The record reports
  extension `mysqli`, the hand-declared signature, and one sink of the
  canonical SQL injection category at the first argument, unconditional.
- **Enumeration:** every sink of the SQL injection category, each naming
  the built-in it belongs to; every method named `query` whatever its
  owner, for a consumer that has not resolved the receiver yet.
- **Boundary:** `strlen` is declared by the generated set and restated by
  the value rules set. The record's flow is the reviewed one; the
  signature and extension are the generated ones.
- **Conditional facts:** `filter_var` answers one unconditional sanitizer
  and five sanitizers each conditioned on the second argument being one
  filter constant. The consumer keeps the ones whose condition matches
  its call; this library ranks nothing among them.
- **Extension:** a framework team ships `laravel-sinks/` with a sinks
  document for `DB::raw`. The consumer builds a lookup over the bundled
  sets plus that directory; `DB::raw` answers as a sink, every bundled
  built-in answers as before.

Software structure: [design-lookup.md](design-lookup.md).
