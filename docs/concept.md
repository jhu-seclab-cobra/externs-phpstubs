# PHP Stubs — Concept

## 1. Context

**Problem Statement**
PHP static analyses must recognise builtin declarations they never see the
body of: whether a name is a builtin function, class, method, or constant,
which PHP extension provides it, what its signature looks like, what a
constant's value is, and which builtins psalm declares source Facts, sink
Facts, and sanitizer Facts for. This knowledge is extracted from upstream
sources and is independent of any analysis technique. The model format for stating it
exists in commons-phpmodels; what remains is the data, its merge into one
body of Facts, and a lookup that answers by PHP name in one vocabulary.

**System Role**
This library supplies generated and manual Document Sets and the lookup over their Set Merge; commons-phpmodels owns the format, decoding and validation.

**Data Flow**
- **Inputs:** upstream stub sources, psalm's taint data, and the Argus
  lists (offline); five bundled document sets.
- **Outputs:** one `BuiltinRecord` per PHP name: extension, signature, flows,
  source Facts, sink Facts, sanitizer Facts, and throws in the Canonical Vocabulary; the same Facts enumerable by kind.
- **Connections:** upstream stubs → extraction → model documents; psalm
  taint data → extraction, Argus lists → review → document sets; all sets
  → [commons-phpmodels decode] → merge → `BuiltinLookup` → consumers.

**Scope Boundaries**
- **Owned:** the generated model documents, the language-construct
  document, PHP extension placement, document discovery, the
  taint sets in psalm's names, the value rules set, every shipped set's
  provenance, the Canonical Vocabulary, the merge, and `BuiltinLookup`.
- **Not Owned:** the model format, the document-set convention, their
  validation, and condition matching (commons-phpmodels); a call's
  argument values, the rule for an undecidable condition, computing a
  call's result, and compiled artifacts (consumers).

## 2. Concepts

**Conceptual Diagram**
```
Offline (per upstream release):
    phpstorm-stubs, psalm stubs ──extraction──► models/<category>/<extension>.yaml
    php-src stubs, C sources ───php-src tools► hierarchies, signatures, throws of models/** (concept-extraction.md)
                                                models/{language,manual}/*.yaml (hand-declared)
    psalm taint data ───────────extraction──► taint/** (document set)
    Argus sink lists ───────────review──────► taint-rules/** (document set)
    reviewed value units ───────review──────► value-rules/** (document set)

Runtime:
    models/** ──manifest──► commons-phpmodels decode ──► generated set
    value-rules/** ─────────────────────────────────────┐
    vocabulary (canonical) ─────────────────────────────┤──► this library's merge ──► BuiltinRecord
    taint/** + mapping onto canonical names ────────────┤                                  │
    taint-rules/** + the same mapping ──────────────────┘                                  ▼
                                                                                   BuiltinLookup by PHP name
```

**Core Concepts**

- **Name:** [Model](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/d356ff45becb5983fc66ac544a00df6618ac224b/docs/glossary/glossary-models.md#model).
- **Role:** Models carry the declaration and assertion data imported from upstream sources.
- **Scope:** Builtin declarations and assertion-only Models.
- **Relationships:** The format loader decodes Models; Set Merge selects their units in force.

- **Name:** [Generated Layer](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/d356ff45becb5983fc66ac544a00df6618ac224b/docs/glossary/glossary-sets.md#generated-layer).
- **Role:** Reproducible generated data supplies the default declaration and taint assertions.
- **Scope:** Generated declarations and generated taint Models.
- **Relationships:** The extraction tools supply the Generated Layer; manual sets supply corrections.

## 3. Contracts & Flow

**Data Contracts**
- **With commons-phpmodels:** every document is decoded by the format
  library's set loader; a format violation, or a conflict the merge finds
  between sets, is a load failure at the consumer's start or in this
  repository's tests — never a silent miss. This library adds no rule of
  the format.
- **With a consumer:** a name lookup returns one `BuiltinRecord` or
  nothing. Signature fields and constant values are read as
  commons-phpmodels types; flows, source Facts, sink Facts, sanitizer Facts,
  and throws are read from the record in the Canonical Vocabulary,
  conditions attached. The consumer holds no merge state: no loaded set, mapping, or precedence.
- **With the extraction tools:** generated documents are reproducible
  from the same upstream versions; a re-run yields identical files.

**Internal Processing Flow:** Upstream data becomes Document Sets, which the lookup loads for callers; the owning [procedure and software mapping](design.md) specifies this concern’s processing.

## 4. Scenarios

- **Typical:** an analysis meets `substr($s, 1)`. `BuiltinLookup`
  answers the record with extension `standard`, its signature, and the
  flow from the first argument to the result.
- **Boundary:** A generated Signature may retain a declared union type; a malformed declared type fails loading and must be corrected in its producer.
- **Interaction:** a consumer asks the record of `mysqli::query` for
  its sinks and receives one sink of the canonical SQL injection vulnerability type
  at the first argument, translated from psalm's `sql`. It asks `strlen`
  for its flow and receives the value rules entry's flow, the signature and
  extension staying the generated set's. The sets meet per subject, condition,
  and unit in this library's merge, never in the consumer.

Lookup: [concept-lookup.md](concept-lookup.md). Sets: [concept-taint.md](concept-taint.md), [concept-taint-rules.md](concept-taint-rules.md), [concept-value-rules.md](concept-value-rules.md).
Software structure: [design.md](design.md). Format semantics: commons-phpmodels [model-declarations.md](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/d356ff45becb5983fc66ac544a00df6618ac224b/docs/model-declarations.md).
