# PHP Stubs — generated taint Document Set Concept

## 1. Context

**Problem Statement**
psalm states which PHP builtins consume a value dangerously (sink Facts),
which neutralize a value for one vulnerability type (sanitizer Facts), and
which produce attacker-controlled data (source Facts). That knowledge is spread over a
dictionary, docblock annotations in psalm's stubs, and psalm's own analyzer
code, all keyed by psalm's kind names. This library needs it as one
document set in the commons-phpmodels format, kept in psalm's names so the
extraction stays a faithful copy; the translation into the canonical
vocabulary happens once, at this library's merge.

**System Role**
The taint document set is the second generated artifact of this library:
a classpath root laid out by the commons-phpmodels document-set convention,
merged by this library into its `BuiltinRecord`s under its own vocabulary mapping
onto the Canonical Vocabulary ([concept.md](concept.md)).

**Data Flow**
- **Inputs:** psalm's internal sink dictionary, taint annotations in
  psalm's stubs, and the superglobal source rule in psalm's analyzer
  (offline, one psalm release).
- **Outputs:** one document set: manifest, vocabulary, policy, and the
  sink, sanitizer, and source documents.
- **Connections:** psalm release → taint extraction → taint document set →
  [commons-phpmodels set loader + this library's mapping] → merge.

**Scope Boundaries**
- **Owned:** the set's files, psalm's kind names as its vocabulary, the
  reproducible extraction, and the classpath root constant that names it.
- **Not Owned:** the Canonical Vocabulary and the mapping from psalm's
  names onto it ([concept.md](concept.md)), and any lookup over the set:
  the set is read only by the merge.

## 2. Concepts

**Conceptual Diagram**
```
psalm dictionaries/InternalTaintSinkMap.php ─┐
psalm stubs/**  @psalm-taint-sink|escape|source ┼─extraction─► taint/
psalm analyzer  superglobal source rule ───────┘             ├── index.txt
                                                             ├── vocabulary.yaml
                                                             ├── policy.yaml
                                                             ├── sinks.yaml
                                                             ├── sanitizers.yaml
                                                             └── sources.yaml
merge: set loader(taint/, canonical vocabulary, mapping) ─► entries in canonical names
```

**Core Concepts**

- **Name:** [Document Set](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/glossary/glossary-sets.md#document-set).
- **Role:** A generated set keeps upstream assertions reproducible independently of consumer naming.
- **Scope:** The taint vocabulary, policy and source/sink/sanitizer Models.
- **Relationships:** The format loader decodes each Document Set before Set Merge consumes it.

- **Name:** [Vocabulary Mapping](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/glossary/glossary-sets.md#vocabulary-mapping).
- **Role:** Translation exposes the Canonical Vocabulary without rewriting the generated inputs.
- **Scope:** Every name used by the generated and manual taint Models.
- **Relationships:** Mapped Models use Canonical Vocabulary names; explicit discards remove assertions without a remaining name.

## 3. Contracts & Flow

**Data Contracts**
- **With commons-phpmodels:** the set follows the document-set convention:
  manifest, optional vocabulary and policy under fixed names, documents
  in manifest order. Every entry decodes through the format library; a
  format violation fails this repository's tests, never a consumer's
  start (every bundled set loads on the first access to the lookup).
- **With the merge:** this library opens the set at its root constant and
  loads it through the set loader with the Canonical Vocabulary as context
  and a vocabulary mapping that lists every psalm kind and the source kind
  `input`. An unlisted name fails loading; only a name explicitly mapped to discard is dropped.

**Internal Processing Flow:** Upstream data becomes Document Sets, which the lookup loads for callers; the owning [procedure and software mapping](design-taint.md) specifies this concern’s processing.

## 4. Scenarios

- **Typical:** psalm's dictionary lists `mysqli_query` with its second
  argument as `sql`. The sinks document states subject `mysqli_query`,
  port `argument(1)`, vulnerability type `sql`. The mapping renames `sql`
  to the canonical SQL injection vulnerability type at the merge.
- **Boundary:** psalm neutralizes `html` in `filter_var` only when the
  filter argument equals one of five sanitize-filter values. The set states
  five conditional entries, one per value; a call matching none keeps no
  sanitizer Fact.
- **Interaction:** the mapping discards psalm's `has_quotes`. The
  `urlencode` entry, which neutralizes `html` and `has_quotes`, arrives with
  `html` alone; an entry whose every kind is discarded arrives not at all.
  The format library applies these explicit mapping entries.

Software structure: [design-taint.md](design-taint.md).
