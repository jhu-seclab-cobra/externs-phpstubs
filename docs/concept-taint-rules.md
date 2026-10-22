# PHP Stubs — Taint Rules Document Set Concept

Extends [concept-taint.md](concept-taint.md) with the one concern it does
not cover: the hand-maintained taint assertions that go beyond psalm's.
The taint document set, psalm kinds, and taint entries are defined there
and used here unchanged.

## 1. Context

**Problem Statement**
psalm's taint data misses sink facts, sanitizer facts, and source facts
that published PHP analyses treat as standard: the Argus sink lists
(Jahanshahi and Egele, USENIX Security 2024), output builtins such as `echo`, callback-taking
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
- **Owned:** the set's files, the four names it adds to psalm's vocabulary,
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
                                ├── vocabulary.yaml   (+ xpath, scheme; + external, path)
                                ├── policy.yaml       (input → xpath, scheme; external → every kind; path → every kind but scheme)
                                ├── sinks.yaml
                                ├── sanitizers.yaml
                                └── sources.yaml
merge: set loader(taint/, …) then set loader(taint-rules/, taint vocabulary, mapping)
```

**Core Concepts**

- **Name:** Taint Rules Document Set
- **Definition:** The bundled hand-maintained document set holding taint
  assertions psalm does not state, in the commons-phpmodels format and in
  psalm's kind names plus four additions of its own.
- **Scope:** sink facts from the Argus lists that the format can express,
  the sanitizer facts and source facts those lists and the builtin name
  list imply, the checks of the type predicates and character checks psalm
  lacks, and nothing psalm already states identically.
- **Relationships:** loaded over the Taint Document Set's vocabulary;
  mounted by the merge above it.

- **Name:** Vocabulary Addition
- **Definition:** A vulnerability type or source kind the set declares
  because psalm has no name for it: the kinds `xpath` (XPath injection) and
  `scheme` (scheme injection: a value at the start of a URL attribute value
  chooses the scheme), and the source kinds `external` (data read from the
  environment, files, sockets, mail, LDAP, or stored records) and `path`
  (the `$_SERVER` keys `PHP_SELF`, `REQUEST_URI`, `SCRIPT_NAME`, `PATH_INFO`,
  which the web server resolves to a path; the policy withholds `scheme`
  from it).
- **Scope:** the four names; every other name in the set is a Psalm Kind.
- **Relationships:** declared in the set's vocabulary, enabled by its
  policy rows, translated by the library's mapping like a Psalm Kind.

- **Name:** Receiver-triggered Sink
- **Definition:** A dangerous operation the Argus lists attribute to the
  object a method is called on rather than to an argument, such as the
  Phar and SPL getters that deserialize on access. `Phar::getMetadata` and
  `PharFileInfo::getMetadata` are such sinks: PHP 8 reads phar metadata
  lazily, so only these getters deserialize it.
- **Scope:** excluded; the format admits argument ports only for sinks. The
  `unserialize` sink point of the file functions is dropped for the same
  reason, because opening a phar path runs no `__wakeup`.
- **Relationships:** documented in the sinks document header; a format
  extension would readmit them.

## 3. Contracts & Flow

**Data Contracts**
- **With the taint document set:** the taint rules set decodes only over the
  taint set's vocabulary; every Psalm Kind it names is declared there. No
  entry equals the taint set's entry for the same subject, condition, and
  section. A taint rules entry for a subject and section the taint set
  also states restates every point of psalm's section and adds its own:
  the merge replaces one section per subject at a time, so the entry is a
  strict superset, never a rewrite. The shipped set has such
  entries among its sinks and sanitizers.
- **With the merge:** this library loads the set with the same psalm
  mapping as the taint set, extended by the four Vocabulary Additions.
  Every output sink of cross-site scripting has a `scheme` twin on the same
  port, and the sanitizers that encode the characters that fix a scheme
  (`urlencode`, `rawurlencode`, `curl_escape`) and the value-typing
  sanitizers cover `scheme`; the HTML escapes do not.
  Mounting it after the taint set makes each taint rules section override
  psalm's for that subject.

**Internal Processing Flow**
1. Select — take each Argus sink the format can express, drop those
   psalm already states with the same ports and kinds.
2. Restate — for a subject psalm also states, copy psalm's points first.
3. Emit — write the vocabulary additions, the policy rows, and the three
   documents sorted by subject.
4. Verify — the repository test loads the set over the taint vocabulary
   and asserts the shape, non-repetition, and superset rules.

## 4. Scenarios

- **Typical:** Argus lists `mail` with its additional-parameters argument
  as a command-injection sink. The sinks document states subject `mail`,
  port `argument(4)`, vulnerability type `shell`.
- **Boundary:** psalm states `readfile` as a `file` sink; Argus adds
  server-side request forgery and output. The taint rules entry states all
  three kinds, and the test proves it contains psalm's point.
- **Boundary:** `$_SERVER['REQUEST_URI']` is a `path` source and
  `$_SERVER['HTTP_REFERER']` an `input` source. Written at the start of an
  `href`, the second can open `javascript:`, the first cannot.
- **Interaction:** the mapping translates `external` and `path` to the
  canonical source kinds and `xpath` and `scheme` to the canonical
  vulnerability types. `getenv` is
  answered as a source of that source kind; `DOMXPath::query` as a sink of
  that vulnerability type; the
  `external` policy row in canonical names.

Software structure: [design-taint-rules.md](design-taint-rules.md).
