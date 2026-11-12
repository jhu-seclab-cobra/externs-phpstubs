# PHP Stubs — manual taint Document Set Concept

## 1. Context

**Problem Statement**
psalm's taint data misses sink Facts, sanitizer Facts, and source Facts
that published PHP analyses treat as standard: the Argus sink lists
[@argus-artifact], output builtins such as `echo`, callback-taking
builtins, LDAP and XPath queries, and data read from the environment,
files, sockets, and stored records. This library states them as one more
document set in the same format and the same names, so that the psalm
mapping serves both at the merge.

**System Role**
The taint rules document set is the third shipped artifact of this library: a
classpath root laid out by the commons-phpmodels document-set convention,
written by hand, kept in psalm's names, and merged after the taint set
under the same mapping into this library's `BuiltinRecord`s.

**Data Flow**
- **Inputs:** the Argus sink lists, the psalm kind names, and the list
  of builtin names this library declares (offline, reviewed by hand).
- **Outputs:** one document set: manifest, vocabulary additions, policy
  rows, and the sink, sanitizer, and source documents.
- **Connections:** Argus lists + review → taint rules document set →
  [commons-phpmodels set loader + this library's mapping] → merge,
  mounted above the taint set.

**Scope Boundaries**
- **Owned:** the set's files, the two names it adds to psalm's vocabulary,
  the choice of which subjects and ports it states, and the classpath root
  constant that names it.
- **Not Owned:** psalm's own assertions (the taint set), the Canonical
  Vocabulary and mapping ([concept.md](concept.md)), and any lookup over
  the set.

## 2. Concepts

**Conceptual Diagram**
```
Argus sink lists ──review──┐
psalm kind names ──────────┼──► taint-rules/
builtin name list ─────────┘    ├── index.txt
                                ├── vocabulary.yaml   (+ xpath, + external)
                                ├── policy.yaml       (input → xpath; external → every kind)
                                ├── sinks.yaml
                                ├── sanitizers.yaml
                                └── sources.yaml
merge: set loader(taint/, …) then set loader(taint-rules/, taint vocabulary, mapping)
```

**Core Concepts**

- **Name:** [Document Set](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/glossary/glossary-sets.md#document-set).
- **Role:** Hand-maintained assertions cover endpoints and argument positions absent from the generated taint data.
- **Scope:** The taint vocabulary, policy and source/sink/sanitizer Models.
- **Relationships:** The format loader decodes each Document Set before Set Merge consumes it.

- **Name:** [Vocabulary Mapping](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/glossary/glossary-sets.md#vocabulary-mapping).
- **Role:** One translation serves generated and hand-maintained taint Models.
- **Scope:** Every name used by the generated and manual taint Models.
- **Relationships:** Mapped Models use Canonical Vocabulary names; explicit discards remove assertions without a remaining name.

## 3. Contracts & Flow

**Data Contracts**
- **With the taint document set:** the taint rules set decodes only over the
  taint set's vocabulary; every Psalm kind it names is declared there. No
  entry equals the taint set's entry for the same subject, condition, and
  section. A taint rules entry for a subject and section the taint set
  also states restates every point of psalm's section and adds its own:
  the merge replaces one section per subject at a time, so the entry is a
  strict superset, never a rewrite. The shipped set has two such
  entries, both sinks.
- **With the merge:** this library loads the set with the same psalm
  mapping as the taint set, extended by the two Vocabulary Additions.
  Mounting it after the taint set makes each taint rules section override
  psalm's for that subject.

**Internal Processing Flow:** Upstream data becomes Document Sets, which the lookup loads for callers; the owning [procedure and software mapping](design-taint-rules.md) specifies this concern’s processing.

## 4. Scenarios

- **Typical:** Argus lists `mail` with its additional-parameters argument
  as a command-injection sink. The sinks document states subject `mail`,
  port `argument(4)`, vulnerability type `shell`.
- **Boundary:** psalm states `readfile` as a `file` sink; Argus adds
  server-side request forgery and output. The taint rules entry states all
  three kinds, and the test proves it contains psalm's point.
- **Interaction:** the mapping translates `external` to the canonical
  source kind and `xpath` to the canonical vulnerability type. `getenv` is
  answered as a source of that source kind; `DOMXPath::query` as a sink of
  that vulnerability type; the
  `external` policy row in canonical names.

Software structure: [design-taint-rules.md](design-taint-rules.md).

## Rationale and Rejected Alternatives

- **Choice:** Keep receiver-triggered deserialization outside the argument-port sink data. PHP 8 reads Phar metadata lazily; `Phar::getMetadata` and `PharFileInfo::getMetadata` deserialize when called, while merely opening a Phar path does not run `__wakeup`.
- **Rejected:** Treating the receiver as an argument would state a different input location. The sink format’s supported locations remain defined by commons-phpmodels; the exclusion is explicit in the resource’s provenance header.
