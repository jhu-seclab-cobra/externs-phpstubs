# PHP Stubs — manual Value unit Document Set Concept

## 1. Context

**Problem Statement**
The generated set carries a value unit (returns with
propagation and optionally characters) only where psalm annotates a flow. For most builtins no
annotation exists, so a consumer falls back to its conservative default:
an unknown value of any type that every argument influences. Where an annotation
exists it is sometimes wider or narrower than the flow the PHP manual
supports. The corrections are consumer-independent Facts about PHP
builtins, so they belong beside the generated set, where every
consumer reads them, not inside one analyzer's configuration.

**System Role**
The value rules document set is the fourth shipped artifact of this
library: a hand-maintained classpath root in the commons-phpmodels
document-set convention holding value units only, declared
manually verified, so that the merge, ranking sets by verification, lets
each unit override the generated one for its subject.

**Data Flow**
- **Inputs:** hand-reviewed value units, checked against the
  generated set and the PHP manual (offline).
- **Outputs:** one document set: manifest, provenance, and value documents
  grouped by PHP manual area.
- **Connections:** review → value rules document set →
  [commons-phpmodels set loader] → this library's merge by precedence.

**Scope Boundaries**
- **Owned:** the set's files, its provenance, the choice of which subjects
  it states, the rule that every stated subject exists in the generated
  declarations, the recorded reason for every unit that differs from a
  generated one, and the classpath root constant that names it.
- **Not Owned:** taint sections (the taint sets), the generated unit it
  overrides, the merge ([concept-lookup.md](concept-lookup.md)), the
  consumer's conservative default, and the consumer's value summary.

## 2. Concepts

**Conceptual Diagram**
```
hand review against models/ and the PHP manual ──────────────► value-rules/
                                                                    ├── index.txt
                                                                    ├── provenance.yaml  (manual)
                                                                    └── <area>.yaml      (value units only)
merge: models/ (generated) ◄──ranked below── value-rules/ (manual), per subject and unit
```

**Core Concepts**

- **Name:** [Value unit](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/d356ff45becb5983fc66ac544a00df6618ac224b/docs/glossary/glossary-models.md#value-unit).
- **Role:** A reviewed unit states a return classification and exhaustive flows together so replacement preserves their coupling.
- **Scope:** Function and method Models whose generated declaration exists.
- **Relationships:** A reviewed Value unit replaces its generated counterpart whole under Set Merge.

## 3. Contracts & Flow

**Data Contracts**
- **With the generated set:** every subject the set states has a
  generated entry; no default-branch unit equals the generated unit of the
  same subject.
- **With the merge:** this library mounts the set unmapped; the set names
  no vulnerability type or source kind and needs no vocabulary. Its provenance is manual,
  so under the default precedence its units outrank the generated ones
  whatever the mount order.

**Internal Processing Flow:** Upstream data becomes Document Sets, which the lookup loads for callers; the owning [procedure and software mapping](design-value-rules.md) specifies this concern’s processing.

## 4. Scenarios

- **Typical:** `strlen` has a signature and no flow annotation. The set
  states `returns: num` with the first argument flowing to the result; the
  consumer's value summary is an unknown value of the declared return type
  instead of an unknown value of any type.
- **Boundary:** `print_r` returns its rendering only when the second
  argument is true. A conditional entry states that case; the
  unconditional entry states a boolean result with no flow.
- **Interaction:** `mysqli::query` takes its signature and throws section
  from the php-src extraction ([concept-extraction.md](concept-extraction.md));
  the `database` document states its reviewed flow from the query argument
  into the result, ranked above the generated unit.

Software structure: [design-value-rules.md](design-value-rules.md).
