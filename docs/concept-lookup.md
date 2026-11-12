# PHP Stubs — Lookup Concept

The lookup reads [Models and Matching Subjects](glossary/glossary.md) through the contracts below.

## 1. Context

**Problem Statement**
Consumers need one lookup over the shipped Document Sets in the Canonical Vocabulary. Per-consumer merging would duplicate ordering, translation and precedence rules.

**System Role**
This concern is the library's read surface: it fixes the vocabulary every
Fact is stated in, merges the shipped sets once, and answers by PHP name.
It adds no Fact of its own and evaluates no condition: a Fact is returned
with its condition attached, and the consumer, which alone knows the call,
decides.

**Data Flow**
- **Inputs:** the generated set, the value rules set, the Canonical Vocabulary and policy, the taint set and the taint rules set with the
  one mapping that translates them; optionally consumer sets.
- **Outputs:** one `BuiltinRecord` per PHP name; the returns, flows,
  source Facts, sink Facts, sanitizer Facts, and throws of every record
  enumerable by kind.
- **Connections:** sets → Set Merge → `BuiltinLookup` → consumers.

**Scope Boundaries**
- **Owned:** the Canonical Vocabulary, the mapping onto it, the mount
  order and the Set Merge (which set's entry is in force per subject,
  condition, and unit), the exact lookup by PHP spelling, and
  enumeration by declaration kind and by Fact kind, and typed queries over
  canonical function/class names ([lookup model](model-lookup.md)). Other
  loose matches remain consumer filters over enumeration.
- **Not Owned:** the format and its decoding (commons-phpmodels); deciding
  whether a Fact's condition holds at a call, and computing a call's
  result (consumers).

## 2. Concepts

**Conceptual Diagram**
```
generated set ──────────────────┐
value-rules/ (manual) ──────────┤
canonical vocabulary + policy ──┤──► Set Merge (manual over generated, per subject / condition / unit)
taint/ ──── mapping ────────────┤                       │
taint-rules/ ── same mapping ───┘                       ▼
consumer: PHP name ────────► BuiltinLookup ────► BuiltinRecord ────► signature, returns, flows, sourceFacts, sinkFacts, sanitizerFacts, throws
consumer: declaration kind ─► BuiltinLookup ────► every record of that kind, filtered by the consumer
consumer: fact kind ────────► BuiltinLookup ────► every fact of that kind, each naming its record
```

**Core Concepts**

- **Name:** [Canonical Vocabulary](glossary/glossary-lookup.md#canonical-vocabulary).
- **Role:** Consumers read every taint assertion under one set of names.
- **Scope:** The vulnerability and input-kind names listed in the lookup model.
- **Relationships:** Vocabulary Mapping translates upstream names before Facts reach callers.

- **Name:** [Set Merge](glossary/glossary-lookup.md#set-merge).
- **Role:** Consumers read the assertions in force without implementing precedence themselves.
- **Scope:** Mounted Models under each distinct Condition and replacement unit.
- **Relationships:** Builtin records expose the resulting Signature and Facts.

- **Name:** [Fact](glossary/glossary-lookup.md#fact).
- **Role:** Consumers receive each assertion with its owning Matching Subject and Condition.
- **Scope:** Source, sink, sanitizer, flow, characters, returns and throws assertions.
- **Relationships:** Each Fact names its owning Matching Subject and carries its Condition.

## 3. Contracts & Flow

**Data Contracts**
- **With commons-phpmodels:** each set is decoded and validated there; the
  merge here ranks by the set provenance each set declares.
- **With the document sets:** each set stays valid on its own; the
  repository test merges all of them and fails on an undeclared name, a
  conflicting redeclaration, or a mapping that omits a psalm kind.
- **With consumers:** a lookup takes a PHP spelling and answers a record
  or nothing; a name that is not a PHP identifier spelling is an argument
  error. Every Fact is returned with its condition; the consumer matches
  the condition against the call's arguments with the format library's one
  matching operation and applies its own rule to an undecidable outcome.
- **With consumer sets:** a consumer that ships its own document set
  obtains a second lookup over the bundled sets plus its own, mounted
  after them, from a directory or classpath root. The set follows the
  document-set convention and names only the Canonical Vocabulary or its
  own additions; without a provenance document it ranks as manual.

**Internal Processing Flow:** Upstream data becomes Document Sets, which the lookup loads for callers; the owning [procedure and software mapping](spec-merge.md) specifies this concern’s processing.

## 4. Scenarios

- **Typical:** `mysqli::query` asked by owner and name. The record reports
  extension `mysqli`, the generated Signature, and one sink of the
  canonical SQL injection vulnerability type at the first argument, unconditional.
- **Enumeration:** every sink of the SQL injection vulnerability type, each naming
  the builtin it belongs to; every method named `query` whatever its
  owner, for a consumer that has not resolved the receiver yet.
- **Boundary:** `strlen` is declared by the generated set and restated by
  the value rules set. The record's flow is the reviewed one; the
  signature and extension are the generated ones.
- **Conditional Facts:** `filter_var` answers five sanitizer Facts each conditioned on the second argument being one
  filter constant, with no unconditional sanitizer Fact. The consumer keeps the ones whose condition matches
  its call; this library ranks nothing among them.
- **Consumer set:** a framework team ships `laravel-sinks/` with a sinks
  document for `DB::raw`. The consumer builds a lookup over the bundled
  sets plus that directory; `DB::raw` answers as a sink, every bundled
  builtin answers as before.

## 5. Rationale and Rejected Alternatives

- **Choice:** Set Merge exposes the result of combining Document Sets under one precedence rule.
- **Rejected:** Requiring callers to retain loaded sets and reproduce the merge makes their answers depend on duplicate policy implementations.

Software structure: [design-lookup.md](design-lookup.md).
