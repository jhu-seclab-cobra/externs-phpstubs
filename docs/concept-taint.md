# PHP Stubs — Taint Document Set Concept

Extends [concept.md](concept.md) with the one concern it does not cover:
the generated taint assertions. Context, generated-set concepts, and the
extraction pipeline are defined there and used here unchanged.

## 1. Context

**Problem Statement**
psalm states which PHP built-ins consume a value dangerously (sinks), which
neutralize a value for one danger kind (escapes), and which produce
attacker-controlled data (sources). That knowledge is spread over a
dictionary, docblock annotations in psalm's stubs, and psalm's own analyzer
code, all keyed by psalm's kind names. This library needs it as one
document set in the commons-phpmodels format, kept in psalm's names so the
extraction stays a faithful copy; the translation into the canonical
vocabulary happens once, at this library's merge.

**System Role**
The taint document set is the second generated artifact of this library:
a classpath root laid out by the commons-phpmodels document-set convention,
merged by this library into its Built-in Records under its own category mapping
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

- **Name:** Taint Document Set
- **Definition:** The bundled document set holding psalm's taint
  assertions in the commons-phpmodels format: a manifest, a vocabulary
  declaring psalm's kind names, a policy stating psalm's rule that input
  reaches every kind, and three documents split by section kind.
- **Scope:** every sink psalm's dictionary lists, every sink, escape, and
  source annotation in psalm's stubs, and the superglobals psalm's analyzer
  colors. Nothing hand-added.
- **Relationships:** a Generated Layer artifact; produced by the Taint
  Extraction; loaded by the merge, never as the generated set.

- **Name:** Psalm Kind
- **Definition:** One of psalm's taint kind names (`sql`, `html`, `shell`,
  `eval`, `file`, `ssrf`, ...), used verbatim as a danger category in the
  set's vocabulary and every sink and sanitizer. Psalm's single origin
  `input` is the set's one origin color.
- **Scope:** the closed list psalm's kind enumeration declares for one
  release; a kind the set declares but no document names stays declared.
- **Relationships:** referenced by every taint entry; translated by the
  library's mapping at the merge; never renamed in the set.

- **Name:** Taint Entry
- **Definition:** A model entry with no signature whose body holds exactly
  one taint section: sinks with one argument port per dangerous argument,
  sanitizers with the escaped kinds, or sources producing `input`. A
  conditional escape (an escape that holds only under one argument value)
  is an entry whose condition states that value at its position.
- **Scope:** function, method, and predefined-variable subjects.
  A variadic dangerous parameter is stated at the variadic's position.
- **Relationships:** a Model Entry; its Subject may or may not exist in
  the generated set — the set states psalm's data, not the generated set's.

- **Name:** Taint Extraction
- **Definition:** The offline producer for the set: one script in this
  repository that reads a psalm checkout and emits every file of the set
  deterministically. Re-running on the same release yields identical
  files; a psalm upgrade is a re-run plus a review of the diff.
- **Scope:** development tooling. Verification of the output is the
  library's decode in this repository's tests.
- **Relationships:** an Extraction Pipeline; produces the Taint Document
  Set.

## 3. Contracts & Flow

**Data Contracts**
- **With commons-phpmodels:** the set follows the document-set convention:
  manifest, optional vocabulary and policy under fixed names, documents
  in manifest order. Every entry decodes through the format library; a
  format violation fails this repository's tests, never a consumer's
  start (every bundled set loads on the first access to the lookup).
- **With the merge:** this library opens the set at its root constant and
  loads it through the set loader with the Canonical Vocabulary as context
  and a category mapping that lists every psalm kind and the origin
  `input`. Names the mapping omits are dropped by the format library;
  nothing is dropped here.

**Internal Processing Flow**
1. Extract — read psalm's dictionary, stub annotations, and source rule.
2. Normalize — spell subjects in PHP identity form, resolve parameter
   names to argument positions from the stub signature, merge duplicate
   statements.
3. Emit — write the vocabulary, the policy, the three documents, sorted
   by subject, each with a producer header naming the psalm release.
4. Verify — the repository test loads the set through the set loader
   with the set's own vocabulary and asserts the expected entries.

## 4. Scenarios

- **Typical:** psalm's dictionary lists `mysqli_query` with its second
  argument as `sql`. The sinks document states subject `mysqli_query`,
  port `argument(1)`, category `sql`. The mapping renames `sql` to the
  canonical SQL injection category at the merge.
- **Boundary:** psalm escapes `html` in `filter_var` only when the filter
  argument equals one of five sanitize-filter values. The set states five
  conditional entries, one per value; a call matching none keeps no escape.
- **Interaction:** the mapping discards psalm's `has_quotes`. The
  `urlencode` entry, which escapes `html` and `has_quotes`, arrives with
  `html` alone; an entry whose every kind is discarded arrives not at all.
  Both decisions are the format library's, driven by the mapping.

Software structure: [design-taint.md](design-taint.md).
