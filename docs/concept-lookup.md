# PHP Stubs — Lookup Concept

Extends [concept.md](concept.md) with the surface a consumer reads: the
canonical vocabulary, the merge of this library's sets, and the lookup by
PHP name. Model Entry, Subject, Stub Registry, Generated Layer, and
Extension Provenance are defined there; Model Index, Branch, Guard
Argument, and Guard Verdict in commons-phpmodels `docs/concept-index.md`.

## 1. Context

**Problem Statement**
Before this concern, a consumer of this library received four document
sets and a registry, and had to merge them itself: choose a mount order,
declare its own vocabulary, write a mapping from psalm's names, rank sets
by provenance, and evaluate guards. Every consumer repeated that work,
and this library could not check that its own sets merge. A consumer that
wants to know what `substr` does, or which built-ins are SQL injection
sinks, should ask by name and read the answer.

**System Role**
This concern is the library's read surface: it fixes the vocabulary every
fact is stated in, merges the shipped sets once through commons-phpmodels,
and answers by PHP name. It adds no fact of its own and no rule of the
merge.

**Data Flow**
- **Inputs:** the Stub Registry, the value rules set, the canonical
  vocabulary and policy, the taint set and the taint rules set with the
  one mapping that translates them.
- **Outputs:** one Built-in Record per PHP name; the flows, sources,
  sinks, and sanitizers of every record enumerable by kind.
- **Connections:** registry + sets → [commons-phpmodels merge] → Model
  Index → Built-in Lookup → consumers.

**Scope Boundaries**
- **Owned:** the Canonical Vocabulary, the mapping onto it, the merge
  order, the exact lookup by PHP spelling, and enumeration by declaration
  kind and by fact kind. Any looser match is the consumer's filter over an
  enumeration, never a rule here.
- **Not Owned:** the merge rule, guard evaluation, and the combination of
  candidate branches (commons-phpmodels); guard arguments from run-time
  values and computing a call's result (consumers).

## 2. Concepts

**Conceptual Diagram**
```
Stub Registry (generated set) ──┐
value-rules/ (manual) ──────────┤
canonical vocabulary + policy ──┤──► commons-phpmodels merge ──► Model Index
taint/ ──── mapping ────────────┤
taint-rules/ ── same mapping ───┘                                     │
                                                                      ▼
consumer: PHP name ────────► Built-in Lookup ──► Built-in Record ──► signature, flows, sources, sinks, sanitizers
consumer: declaration kind ─► Built-in Lookup ──► every record of that kind, filtered by the consumer
consumer: fact kind ────────► Built-in Lookup ──► every fact of that kind, each naming its record
```

**Core Concepts**

- **Name:** Canonical Vocabulary
- **Definition:** This library's own names for danger categories (SQL
  injection, command injection, ...) and origin colors (user input, external
  input), with the policy rows over them. The psalm-named sets are
  translated into it by one category mapping this library ships and
  applies at the merge; a consumer never sees psalm's names and keeps no
  mapping.
- **Scope:** every category and color any shipped set states.
- **Relationships:** context of the merge; the names every Built-in Record
  answers in.

- **Name:** Model Index
- **Definition:** The commons-phpmodels merge of this library's sets in
  its fixed order: the Generated Layer, the value rules set, the Canonical
  Vocabulary, the taint set, the taint rules set. Per subject and section
  the reviewed statement outranks the generated one.
- **Scope:** built once, lazily; internal to the Built-in Lookup.
- **Relationships:** built by commons-phpmodels; read by the Built-in Lookup.

- **Name:** Built-in Record
- **Definition:** What the Built-in Lookup answers for one PHP name: the
  extension, the signature, and, reachable from it, the flows, sources,
  sinks, and sanitizers the Model Index holds for that subject. Each is
  read as the effective statement for the consumer's guard arguments,
  unknown arguments by default. The same facts are enumerable by kind,
  each fact naming the record it belongs to.
- **Scope:** one per subject the Model Index knows; a name the index does
  not know has no record.
- **Relationships:** read from the Model Index; answered by the Built-in
  Lookup; identified by its Subject.

- **Name:** Built-in Lookup
- **Definition:** The entry point consumers use. An exact lookup asks for
  a function, method, class, constant, class constant, or property by its
  PHP spelling — a member either as one `Owner::name` string or as owner
  and name apart — and is answered with its Built-in Record or nothing.
  An enumeration yields every record of one declaration kind, or every
  fact of one fact kind, for the consumer to filter by its own rule: a
  method name across all owners, a constant name compared without case.
  Identity folding stays with the Subject; no resolution rule is added here.
- **Scope:** exact lookup by name; enumeration by declaration kind and by
  fact kind.
- **Relationships:** reads the Model Index; answers consumer queries.

## 3. Contracts & Flow

**Data Contracts**
- **With commons-phpmodels:** the sets are handed over in the fixed order
  with the default precedence; the Model Index is read, never rebuilt or
  re-ranked here. A merge failure is a load failure naming the set.
- **With the document sets:** each set stays valid and complete on its
  own; the repository test merges all of them and fails on an undeclared
  name, a conflicting redeclaration, or a mapping that omits a psalm kind.
- **With consumers:** a lookup takes a PHP spelling and answers a record
  or nothing; a name that is not a PHP identifier spelling is an argument
  error. A fact read without guard arguments is the sound union over the
  subject's branches; a consumer that knows an argument passes it and
  reads the narrower statement.
- **With extension sets:** a consumer that ships its own document set
  obtains a second lookup over the bundled sets plus its own, mounted
  after them, from a directory or classpath root; the default lookup is
  unchanged. The set follows the document-set convention and names only
  the Canonical Vocabulary or its own additions.

**Internal Processing Flow**
1. Merge — build the Model Index once, lazily, from the sets in order.
2. Resolve — parse the lookup name into a Subject through the format
   library's creators, so folding is decided once.
3. Read — take the subject's branches from the index; the record exposes
   each section as the index answers it.
4. Enumerate — walk every subject the index knows and yield the records
   of one declaration kind, or the facts of one fact kind, each with its
   record.

## 4. Scenarios

- **Typical:** `mysqli::query` asked by owner and name. The record reports
  extension `mysqli`, the hand-declared signature, and one sink of the
  canonical SQL injection category at the first argument.
- **Enumeration:** every sink of the SQL injection category, each naming
  the built-in it belongs to, for a consumer that seeds a query by kind;
  every method named `query` whatever its owner, for a consumer that has
  not resolved the receiver yet.
- **Boundary:** `strlen` is declared by the generated set and restated by
  the value rules set. The record's flow is the reviewed one; the
  signature and extension are the generated ones. No consumer sees the
  seam.
- **Interaction:** a consumer meets `print_r($x, true)`. It passes the
  second argument as a guard argument and reads the value semantics of
  the branch that holds; with the argument unknown it reads the join.
- **Extension:** a framework team ships `laravel-sinks/` with a sinks
  document for `DB::raw`. The consumer builds a lookup over the bundled
  sets plus that directory; `DB::raw` answers as a sink, every bundled
  built-in answers as before.

Software structure: [design-lookup.md](design-lookup.md).
