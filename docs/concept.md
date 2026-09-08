# PHP Stubs — Concept

## 1. Context

**Problem Statement**
PHP static analyses must recognise built-in declarations they never see the
body of: whether a name is a built-in function, class, method, or constant,
which PHP extension provides it, what its signature looks like, what a
constant's value is, and which built-ins psalm marks as taint sources, sinks,
and escapes. This knowledge is extracted from upstream sources and is
independent of any analysis technique. The model format for stating it
exists in commons-phpmodels; what remains is the data, its merge into one
index, and a lookup that answers by PHP name in one vocabulary.

**System Role**
This library is the data layer and the lookup surface of the Cobra PHP
model stack: the generated model documents for PHP built-ins, two taint
sets ([concept-taint.md](concept-taint.md), [concept-taint-rules.md](concept-taint-rules.md)),
a value rules set ([concept-value-rules.md](concept-value-rules.md)), and the
vocabulary, merge, and lookup by PHP name over them ([concept-lookup.md](concept-lookup.md)).
The format, decoding, validation, and the merge rule belong to commons-phpmodels.

**Data Flow**
- **Inputs:** upstream stub sources, psalm's taint data, and the Argus
  lists (offline); model documents and three document sets (bundled).
- **Outputs:** one Built-in Record per PHP name: extension, signature, flows,
  sources, sinks, and sanitizers in the canonical vocabulary; the same facts enumerable by kind.
- **Connections:** upstream stubs → extraction → model documents; psalm
  taint data → extraction, Argus lists → review → document sets; all sets
  → [commons-phpmodels decode + merge] → Built-in Lookup → consumers.

**Scope Boundaries**
- **Owned:** the generated model documents, the language-construct
  document, extension provenance, document discovery, the registry, the
  taint sets in psalm's names, the value rules set, every shipped set's
  provenance, and the Lookup Surface.
- **Not Owned:** the model format, the document-set convention, their
  validation, and the merge rule (commons-phpmodels); guard arguments from
  run-time values, branch choice under an undecided guard, computing a
  call's result, and compiled artifacts (consumers).

## 2. Concepts

**Conceptual Diagram**
```
Offline (per upstream release):
    phpstorm-stubs, psalm stubs ──extraction──► models/<category>/<extension>.yaml
                                                models/{language,manual}/*.yaml (hand-declared)
    psalm taint data ───────────extraction──► taint/** (document set)
    Argus sink lists ───────────review──────► taint-rules/** (document set)
    reviewed value semantics ───review──────► value-rules/** (document set)

Runtime:
    models/** ──manifest──► commons-phpmodels decode ──► Stub Registry (generated set)
    value-rules/** ─────────────────────────────────────┐
    vocabulary (canonical) ─────────────────────────────┤──► commons-phpmodels merge ──► Model Index
    taint/** + mapping onto canonical names ────────────┤                                    │
    taint-rules/** + the same mapping ──────────────────┘                                    ▼
                                                                                   Built-in Lookup by PHP name
```

**Core Concepts**

- **Name:** Model Entry
- **Definition:** One declarative statement about one PHP declaration in
  the commons-phpmodels format: a subject naming the declaration and a
  signature section describing it, with a propagation section when the
  upstream data states a flow. The entry is this library's unit of data;
  no parallel record type exists.
- **Scope:** every built-in function, class, method, constant, class
  constant, and property the upstream sources declare.
- **Relationships:** decoded by commons-phpmodels; held by the Stub
  Registry; identified by its Subject.

- **Name:** Subject
- **Definition:** The identity of a PHP declaration as defined by
  commons-phpmodels: a kind plus a PHP-native spelling, case-folded per
  kind. The registry keys every entry by its subject, so identity and
  folding are decided once in the format library and never re-derived here.
- **Scope:** the six declaration kinds the registry carries; predefined
  variables appear only in the taint set.
- **Relationships:** identifies exactly one Model Entry; the target of
  every lookup.

- **Name:** Generated Layer
- **Definition:** The lowest set of this library's merge: documents emitted
  by an extraction producer, whose set provenance declares them generated,
  never hand-edited. A correction belongs in one of this library's
  hand-maintained sets, not in these files.
- **Scope:** every generated document under the models tree (not the
  hand-declared `language/` and `manual/` documents), and the taint set.
- **Relationships:** produced by the Extraction Pipeline; consumed whole by
  the Stub Registry.

- **Name:** Extension Provenance
- **Definition:** The PHP extension that provides a declaration
  (`standard`, `mysqli`, `core`). The model format does not carry it: it
  is a property of where a declaration comes from, not a statement about
  the declaration. It is encoded by document placement — the document's
  file name, with any numeric split suffix removed — and attached to every
  entry of that document at load.
- **Scope:** every entry, including language constructs, which carry the
  extension name of their own document.
- **Relationships:** derived from the Document Manifest layout; served
  beside each Model Entry.

- **Name:** Language Construct Entry
- **Definition:** An entry for a PHP language construct that analyses
  treat as callable or class-like although no extension declares it:
  keyword constructs (`echo`, `isset`, `exit`, `include`, ...) and scalar
  type names used in class position (`int`, `string`, ...), declared as
  data in the models tree so one load path serves every lookup. The
  `manual/` documents declare, the same way, built-ins the Extraction
  Pipeline cannot produce: methods it omits, functions outside its release.
- **Scope:** the closed keyword and scalar-type sets the registry serves
  today.
- **Relationships:** a Model Entry like any other; distinguished only by
  its Extension Provenance.

- **Name:** Stub Registry
- **Definition:** The immutable result of loading every document in the
  manifest: per-kind maps from subject to entry with extension provenance.
  Built once; it enters the merge as the generated set and carries the
  extension each Built-in Record reports.
- **Scope:** internal; existence and entry retrieval for the merge.
- **Relationships:** built from Model Entries; one input of the Model Index.

- **Name:** Lookup Surface
- **Definition:** The Canonical Vocabulary, Model Index, Built-in Record,
  and Built-in Lookup ([concept-lookup.md](concept-lookup.md)): how the
  sets merge and how a consumer reads them.
- **Relationships:** built over the Stub Registry and the document sets.

- **Name:** Document Manifest
- **Definition:** The build-generated list of every model document in the
  resource tree. Discovery reads the manifest, never the classpath
  directory, so packaging in a jar and in a directory behave identically.
- **Scope:** one manifest per resource tree.
- **Relationships:** enumerates the documents the Stub Registry loads;
  its layout defines Extension Provenance.

- **Name:** Extraction Pipeline
- **Definition:** The offline producer: parses upstream sources and emits
  documents directly in the commons-phpmodels format, verified against the
  same decoder consumers use. Runs once per upstream release; committed.
- **Scope:** development tooling, not a runtime dependency; only one
  representation of the corpus exists. The taint extraction is one script
  in this repository ([concept-taint.md](concept-taint.md)).
- **Relationships:** produces the Generated Layer.

## 3. Contracts & Flow

**Data Contracts**
- **With commons-phpmodels:** every document is decoded by the format
  library's set loader and every set merged by its index; a format or
  merge violation is a load failure at the consumer's start or in this
  repository's tests — never a silent miss. This library adds no rule of
  the format and no rule of the merge.
- **With cobraphp-core:** a name lookup returns one Built-in Record or
  nothing. Signature fields and constant values are read as
  commons-phpmodels types; flows, sources, sinks, and sanitizers are read
  from the record in the Canonical Vocabulary, guards attached. The
  consumer holds no set, layer, mapping, or precedence; which set stated a
  fact is answered on request, never required.
- **With the Extraction Pipeline:** generated documents are reproducible
  from the same upstream versions; a re-run yields identical files.

**Internal Processing Flow**
1. Discover — read the Document Manifest.
2. Decode — pass each document to the commons-phpmodels loader; a decode
   failure names the document.
3. Attribute — derive the Extension Provenance from the document's
   placement and attach it to each entry.
4. Register — insert entries into per-kind maps keyed by subject; two
   documents declaring the same subject is a corpus defect and fails the
   load naming both documents.
5. Merge — hand the registry as the generated set, then the value rules
   set, the Canonical Vocabulary, and the two translated taint sets to
   commons-phpmodels; receive the Model Index.
6. Answer — resolve a PHP name to a subject and read its record from the
   index; enumerate a fact kind across the index.

## 4. Scenarios

- **Typical:** an analysis meets `substr($s, 1)`. The Built-in Lookup
  answers the record with extension `standard`, its signature, and the
  flow from the first argument to the result.
- **Boundary:** a generated document carries a union return type. The
  format rejects it at decode, the load fails naming the document, and the
  fix is in the Extraction Pipeline, which simplifies the upstream type
  before emitting — never a hand edit of the generated file.
- **Interaction:** cobraphp-core asks the record of `mysqli::query` for
  its sinks and receives one sink of the canonical SQL injection category
  at the first argument, translated from psalm's `sql`. It asks `strlen`
  for its flow and receives the value rules statement, the signature and
  extension staying the registry's. The sets meet per subject and section
  in the Model Index, never in the consumer.

Lookup: [concept-lookup.md](concept-lookup.md). Sets: [concept-taint.md](concept-taint.md), [concept-taint-rules.md](concept-taint-rules.md), [concept-value-rules.md](concept-value-rules.md).
Software structure: [design.md](design.md). Format semantics: commons-phpmodels `docs/model-declarations.md`.
