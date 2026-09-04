# PHP Stubs — Concept

## 1. Context

**Problem Statement**
PHP static analyses must recognise built-in declarations they never see the
body of: whether a name is a built-in function, class, method, or constant,
which PHP extension provides it, what its signature looks like, what a
constant's value is, and which built-ins psalm marks as taint sources, sinks,
and escapes. This knowledge is extracted from upstream sources and is
independent of any analysis technique. The model format for stating it
exists in commons-phpmodels; what remains is the data, a registry serving
the declarations, and two document sets serving the taint assertions.

**System Role**
This library is the generated layer of the Cobra PHP model stack: it owns
the generated model documents for PHP built-ins, their provenance, a
read-only registry that resolves PHP names to model entries, and two taint
document sets ([concept-taint.md](concept-taint.md), [concept-taint-rules.md](concept-taint-rules.md)).
The format, decoding, and validation belong to commons-phpmodels.

**Data Flow**
- **Inputs:** upstream stub sources, psalm's taint data, and the Argus
  lists (offline); model documents and two taint sets (bundled resources).
- **Outputs:** model entries keyed by subject, each carrying its
  extension provenance; PHP-name lookups over them; the taint document set
  as a classpath root consumers load themselves.
- **Connections:** upstream stubs → extraction → model documents →
  [commons-phpmodels decode] → [this registry] → consumers (cobraphp-core);
  psalm taint data → extraction, Argus lists → review → document sets → consumers.

**Scope Boundaries**
- **Owned:** the generated model documents, the language-construct
  document, extension provenance, document discovery, the registry,
  PHP-name lookup semantics (unqualified member lookup, constant case
  over-approximation), and the taint document set in psalm's names.
- **Not Owned:** the model format, the document-set convention, and their
  validation (commons-phpmodels); the consumer's category vocabulary, its
  mapping from psalm's names, configuration layering, branch selection,
  and compiled artifacts (consumers).

## 2. Concepts

**Conceptual Diagram**
```
Offline (per upstream release):
    phpstorm-stubs, psalm stubs ──extraction──► models/<category>/<extension>.yaml
                                                models/language/*.yaml (hand-declared)
    psalm taint data ───────────extraction──► taint/** (document set)
    Argus sink lists ───────────review──────► taint-rules/** (document set)

Runtime:
    models/** ──manifest──► commons-phpmodels decode ──► Stub Registry
                            (strict, validated)          entries by subject
                                                         + extension provenance
                                                         + lookup indexes
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
- **Definition:** The lowest configuration layer of a consumer, as named in
  commons-phpmodels: documents emitted by an extraction producer, marked
  by a provenance header, never hand-edited. A correction belongs in a
  higher layer of the consumer, not in these files.
- **Scope:** every generated document under the models tree, and every
  file of the taint document set.
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
  type names used in class position (`int`, `string`, ...). These are
  declared as data in one hand-maintained document in the models tree so
  that one load path and one entry type serve every lookup.
- **Scope:** the closed keyword and scalar-type sets the registry serves
  today.
- **Relationships:** a Model Entry like any other; distinguished only by
  its Extension Provenance.

- **Name:** Stub Registry
- **Definition:** The immutable result of loading every document in the
  manifest: per-kind maps from subject to entry, plus the indexes a
  PHP-name lookup needs. Built eagerly once; every lookup afterwards is a
  map read.
- **Scope:** existence, entry retrieval, and bulk subject enumeration.
- **Relationships:** built from Model Entries; queried by the Lookup
  Semantics.

- **Name:** Lookup Semantics
- **Definition:** The name resolution rules this library adds above the
  format's identity rules: a member (method, class constant) may be looked
  up by its unqualified name alone through a suffix index; a constant may
  be looked up case-insensitively as an explicit over-approximation for
  analyses that cannot trust spelling.
- **Scope:** lookup only; identity folding stays with the Subject.
- **Relationships:** operates on the Stub Registry; answers consumer
  queries.

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
  library's model loader; every format violation is a load failure at the
  consumer's start or the extraction's verification — never a silent
  miss. This library adds no validation rule of the format and holds no
  parallel copy of its types.
- **With cobraphp-core:** a name lookup returns the model entry with its
  extension provenance, or nothing. Signature fields, constant values, and
  declared propagations are read from the entry as commons-phpmodels
  types. Taint assertions reach the consumer only through the taint
  document set; layer overrides are never here.
- **With the Extraction Pipeline:** generated documents are reproducible
  from the same upstream versions; a re-run yields identical files.

**Internal Processing Flow**
1. Discover — read the Document Manifest.
2. Decode — pass each document to the commons-phpmodels loader; a decode
   failure names the document.
3. Attribute — derive the Extension Provenance from the document's
   placement and attach it to each entry.
4. Merge — insert entries into per-kind maps keyed by subject; two
   documents declaring the same subject is a corpus defect and fails the
   load naming both documents.
5. Index — build the unqualified-member and case-insensitive-constant
   indexes.
6. Freeze — the registry is immutable from here on.

## 4. Scenarios

- **Typical:** an analysis meets `substr($s, 1)`. The registry resolves the
  function subject, returns the entry with extension `standard`, its
  signature, and the declared flow from the first argument to the result.

- **Boundary:** a generated document carries a union return type. The
  format rejects it at decode, the load fails naming the document, and the
  fix is in the Extraction Pipeline, which simplifies the upstream type
  before emitting — never a hand edit of the generated file.

- **Interaction:** cobraphp-core mounts the whole registry as its generated
  layer beneath its hand-written rule layers. A hand-written entry for
  `htmlspecialchars` adds a sanitizer section; the registry's entry keeps
  supplying the signature and extension. The two layers meet per subject
  and unit in the consumer, not here.

Taint sets: [concept-taint.md](concept-taint.md), [concept-taint-rules.md](concept-taint-rules.md).
Software structure: [design.md](design.md). Format semantics: commons-phpmodels
`docs/model-declarations.md`.
