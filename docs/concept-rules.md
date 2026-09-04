# PHP Stubs — Rules Document Set Concept

Extends [concept-taint.md](concept-taint.md) with the one concern it does
not cover: the hand-maintained taint assertions that go beyond psalm's.
The taint document set, psalm kinds, and taint entries are defined there
and used here unchanged.

## 1. Context

**Problem Statement**
psalm's taint data misses sinks, escapes, and sources that published PHP
analyses treat as standard: the Argus sink lists (Jahanshahi and Egele,
USENIX Security 2024), output built-ins such as `echo`, callback-taking
built-ins, LDAP and XPath queries, and data read from the environment,
files, sockets, and stored records. Consumers need these as one more
document set in the same format and the same names, so that one category
mapping serves both.

**System Role**
The rules document set is the third shipped artifact of this library: a
classpath root laid out by the commons-phpmodels document-set convention,
written by hand, kept in psalm's names, and served to consumers that mount
it after the taint set under the same mapping.

**Data Flow**
- **Inputs:** the Argus sink lists, the psalm kind names, and the corpus
  of built-in names this library declares (offline, reviewed by hand).
- **Outputs:** one document set: manifest, vocabulary additions, policy
  rows, and the sink, sanitizer, and source documents.
- **Connections:** Argus lists + review → rules document set →
  [commons-phpmodels set loader + consumer mapping] → consumer layers,
  mounted above the taint set.

**Scope Boundaries**
- **Owned:** the set's files, the two names it adds to psalm's vocabulary,
  the choice of which subjects and ports it states, and the classpath root
  constant that names it.
- **Not Owned:** psalm's own assertions (the taint set), the consumer's
  vocabulary and mapping, and any runtime lookup over the set.

## 2. Concepts

**Conceptual Diagram**
```
Argus sink lists ──review──┐
psalm kind names ──────────┼──► rules/
built-in name corpus ──────┘    ├── index.txt
                                ├── vocabulary.yaml   (+ xpath, + external)
                                ├── policy.yaml       (input → xpath; external → every kind)
                                ├── sinks.yaml
                                ├── sanitizers.yaml
                                └── sources.yaml
consumer: set loader(taint/, …) then set loader(rules/, taint vocabulary, mapping)
```

**Core Concepts**

- **Name:** Rules Document Set
- **Definition:** The bundled hand-maintained document set holding taint
  assertions psalm does not state, in the commons-phpmodels format and in
  psalm's kind names plus two additions of its own.
- **Scope:** sinks from the Argus lists that the format can express, the
  escapes and sources those lists and the built-in corpus imply, and
  nothing psalm already states identically.
- **Relationships:** loaded over the Taint Document Set's vocabulary;
  mounted by consumers above it; never read by the Stub Registry.

- **Name:** Vocabulary Addition
- **Definition:** A danger category or origin color the set declares
  because psalm has no name for it: the kind `xpath` (XPath injection)
  and the color `external` (data read from the environment, files,
  sockets, mail, LDAP, or stored records).
- **Scope:** the two names; every other name in the set is a Psalm Kind.
- **Relationships:** declared in the set's vocabulary, enabled by its
  policy rows, translated by the consumer's mapping like a Psalm Kind.

- **Name:** Widened Entry
- **Definition:** A rules entry for a subject and section the taint set
  also states. Because a consumer replaces one section per subject at a
  time, the entry restates every point of psalm's section and adds its
  own; it is a strict superset, never a rewrite.
- **Scope:** sinks only in the shipped set; nine subjects.
- **Relationships:** a Taint Entry; validated against the Taint Document
  Set by this repository's tests.

- **Name:** Receiver-triggered Sink
- **Definition:** A dangerous operation the Argus lists attribute to the
  object a method is called on rather than to an argument, such as the
  Phar and SPL getters that deserialize on access.
- **Scope:** excluded; the format admits argument ports only for sinks.
- **Relationships:** documented in the sinks document header; a format
  extension would readmit them.

## 3. Contracts & Flow

**Data Contracts**
- **With the taint document set:** the rules set decodes only over the
  taint set's vocabulary; every Psalm Kind it names is declared there. No
  entry equals the taint set's entry for the same subject, guard, and
  section.
- **With cobraphp-core:** the consumer opens the set at the root constant
  this library exports and loads it with the same category mapping as the
  taint set, extended by the two Vocabulary Additions. Mounting it after
  the taint set makes each rules section override psalm's for that
  subject.

**Internal Processing Flow**
1. Select — take each Argus sink the format can express, drop those
   psalm already states with the same ports and kinds.
2. Restate — for a subject psalm also states, copy psalm's points first.
3. Emit — write the vocabulary additions, the policy rows, and the three
   documents sorted by subject.
4. Verify — the repository test loads the set over the taint vocabulary
   and asserts the shape, non-repetition, and widening rules.

## 4. Scenarios

- **Typical:** Argus lists `mail` with its additional-parameters argument
  as a command-injection sink. The sinks document states subject `mail`,
  port `argument(4)`, category `shell`.
- **Boundary:** psalm states `readfile` as a `file` and `unserialize`
  sink; Argus adds server-side request forgery and output. The rules entry
  states all four kinds, and the test proves it contains psalm's two.
- **Interaction:** the consumer maps `external` to its own color and
  `xpath` to its own category. `getenv` arrives as a source of that color;
  `DOMXPath::query` arrives as a sink of that category; the `external`
  policy row arrives in the consumer's names.

Software structure: [design-rules.md](design-rules.md).
