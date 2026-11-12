# PHP Stubs — Design

The data side of the library: the resource roots, the five bundled sets and
their fixed Mount Order, the generated-set rules, and the
error types. The lookup surface — merge, records, facts, `PhpStubs` — is in
[design-lookup.md](design-lookup.md). Concepts: [concept.md](concept.md),
[concept-lookup.md](concept-lookup.md). Domain semantics:
[model-lookup.md](model-lookup.md). Fold: [spec-merge.md](spec-merge.md).

## Design Overview

- **Classes:** `StubResources` (object), `PhpStubs`, `BuiltinRecord<S>`,
  the seven fact types, `SetMerge`, `Mount` ([design-lookup.md](design-lookup.md));
  the php-src producers ([design-extraction.md](design-extraction.md))
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `Document`, `ResourceOpener`, `VocabularyMappingLoader`,
  `VocabularyMapping`, `ModelEntry`, `ModelSubject` and its seven subtypes,
  `ArgPattern`, `SignatureInfo` and its four subtypes, `Vocabulary`,
  `TaintPolicy`, `Precedence`, `Verification`
- **Relationships:** `StubResources` names the roots and opens them;
  `PhpStubs` mounts the bundled roots in Mount Order through
  `DocumentSetLoader` (the psalm mapping decoded once by
  `VocabularyMappingLoader` and applied to the two psalm-named sets) and
  folds them in `SetMerge`. One-way: facade → `SetMerge` → format library.
- **Exceptions:** `StubIndexNotFoundException`, `StubIndexInvalidException`
  (both extend `RuntimeException`).
- **Dependency roles:** Resource roots and opener: `StubResources`.
  Facade and composition root: `PhpStubs`. Decoder and validator:
  commons-phpmodels.

Package `edu.jhu.cobra.externs.phpstubs`, one module, `explicitApi()`.
commons-phpmodels is an `api` dependency: its subject, signature, section,
and condition types are the record surface. No YAML library is a direct
dependency.

## Class / Type Specifications

### StubResources (object)

**Responsibility:** The classpath roots of every bundled set and the
opener over a root. Value tier: constants, because the layout is fixed by
this repository's build.

**Constants:** `MODELS = "/models/"`, `VALUE_RULES = "/value-rules/"`,
`VOCABULARY = "/vocabulary/"`, `TAINT = "/taint/"`,
`TAINT_RULES = "/taint-rules/"`, `PSALM_MAPPING = "/vocabulary/psalm-mapping.yaml"`.

**Methods:**
- `opener(root: String): ResourceOpener` — resolves a relative document
  path against `root` (trailing slash optional) through
  `Class.getResourceAsStream`; returns `null` for an absent resource.
  `MountSequence` records absences to raise `StubIndexNotFoundException`.

### Mount Order (private `bundledMounts()` of `PhpStubs.kt`)

The bundled mounts, in this order, each with its mapping:

| Position | Root | Mapping | Verification |
|----------|------|---------|--------------|
| 0 | `MODELS` | none | from `models/provenance.yaml` (generated) |
| 1 | `VALUE_RULES` | none | from its provenance (manual) |
| 2 | `VOCABULARY` | none | from its provenance (manual); empty manifest |
| 3 | `TAINT` | `PSALM_MAPPING` | from its provenance (generated) |
| 4 | `TAINT_RULES` | `PSALM_MAPPING` | from its provenance (manual) |

Each set decodes against the vocabulary accumulated over the earlier
positions; a set's own `vocabulary.yaml` merges after it decodes and its
`policy.yaml` rows append. A bundled set without `provenance.yaml` is a
packaging fault, not a default.

**Generated-set rules** (position 0; each violation is a
`StubIndexInvalidException` naming the document and subject):
- No entry has a `VariableSubject`; predefined variables are not stubs.
- Every entry declares a `signature` and no condition.
- No two documents declare the same subject; the message names both.

Constant subjects fold nothing, so `TRUE` and `true` are distinct entries.
The extension of each generated entry is data tier: derived from the
document's placement, never a constant in code.

The other four sets follow their own set rules
([design-taint.md](design-taint.md), [design-taint-rules.md](design-taint-rules.md),
[design-value-rules.md](design-value-rules.md)) and the format library's
duplicate rule per (subject, condition) within one document.

## Resource Layout

```
models/
├── index.txt              # build-generated manifest, sorted relative paths
├── provenance.yaml        # producers tools/convert_stubs.py v2, then the three php-src tools; verification generated
├── core.yaml              # extension "core"
├── language/              # hand-declared language constructs
│   ├── keyword.yaml       # 11 keyword functions + class exit, extension "keyword"
│   ├── scalar.yaml        # classes int, float, string, bool, array, extension "scalar"
│   └── legacy.yaml        # class resource, extension "legacy"
├── manual/<extension>.yaml       # hand-declared builtins php-src 8.5.11 lacks: mysql, standard; core holds the constants declared without a value
├── standard/standard_1..8.yaml   # extension "standard" (split suffix removed)
├── <category>/<extension>.yaml   # crypto, database, file, image, misc, network, system, text, xml
└── <extension>.yaml              # extensions only php-src declares (placement, design-extraction.md)
vocabulary/
├── index.txt              # comment only: the set ships no model document
├── provenance.yaml        # producer externs-phpstubs canonical vocabulary; verification manual
├── vocabulary.yaml        # twelve vulnerability types, two source kinds, with descriptions
├── policy.yaml            # both source kinds enable every vulnerability type
└── psalm-mapping.yaml     # psalm kinds → canonical names; has_quotes, cookie, user_secret, system_secret → ignore
```

A constant whose value depends on the host, the PHP build or the run is
declared without a value: only `manual/core.yaml` declares it, with its type,
and `core.yaml` does not (the generated-set rule allows one document per
subject). They are `PHP_OS`, `PHP_OS_FAMILY`, `DIRECTORY_SEPARATOR`,
`PATH_SEPARATOR`, `PHP_EOL`, `PHP_MAXPATHLEN`, `GLOB_BRACE`, `GLOB_MARK`,
`GLOB_NOSORT`, `GLOB_NOESCAPE`, `GLOB_ONLYDIR`, `PHP_INT_SIZE`, `PHP_INT_MAX`,
`PHP_INT_MIN`, `PHP_PREFIX`, `PHP_BINDIR`, `PHP_LIBDIR`, `PHP_DATADIR`,
`PHP_EXTENSION_DIR`, `PHP_EXTRA_VERSION`, `PHP_VERSION`, `PHP_VERSION_ID`,
`PHP_MAJOR_VERSION`, `PHP_MINOR_VERSION`, `PHP_RELEASE_VERSION`, `PHP_SAPI`,
`STDIN`, `STDOUT` and `STDERR`. A consumer reads a record whose `typedSignature.value` is absent as a
constant of that type with an unknown value.
The generated-set rule above keeps the two layers disjoint: a regeneration that
writes one of these subjects back into `core.yaml` makes the set fail to load,
naming both documents, and `ManualDeclarationsTest` checks the two documents
without loading the set.

Generated documents carry the producer header of commons-phpmodels'
generated layer and are never hand-edited; language, manual, and
vocabulary documents are hand-maintained without one. A keyword function
declares one optional variadic `mixed` parameter and a `mixed` return; a
language class declares `classifier: class`. A manual entry declares its
PHP-manual signature and, where the manual states a flow, a propagation;
the reason is a comment.

The Gradle resource task writes `index.txt` for `models/`, `taint/`,
`taint-rules/`, `value-rules/` (main) and `models-test/` (test), listing
every document except `vocabulary.yaml`, `policy.yaml`, `provenance.yaml`,
and `psalm-mapping.yaml`; `vocabulary/index.txt` and every other test
fixture directory ship their own manifest. Set layouts:
[design-taint.md](design-taint.md), [design-taint-rules.md](design-taint-rules.md),
[design-value-rules.md](design-value-rules.md).

## Exception / Error Types

| Exception | When raised |
|-----------|-------------|
| `StubIndexNotFoundException(resource)` | `index.txt`, a listed document, or the psalm mapping resource is not on the classpath or under an extension directory |
| `StubIndexInvalidException(reason, cause?)` | The set load or merge fails for any other reason (commons-phpmodels cause attached), a bundled set ships without `provenance.yaml`, a generated-set rule is violated, a conditional entry declares a signature, or a class alias collides with another class key ([alias-key step](spec-merge.md#steps)) |
| `IllegalArgumentException` | A lookup name is not a PHP identifier spelling (raised by the commons-phpmodels subject creator) |

Every bundled-set error surfaces on first access to `PhpStubs`; an
extension-set error surfaces from the `with` call that mounts it.

## Validation Rules

- Format validation — YAML strictness, subject spellings, signature shape,
  arity against the parameter list and the condition's positions, declared
  types, vocabulary references, mapping totality — is commons-phpmodels'
  and is not repeated here.
- The generated-set rules run over the generated set before the fold; a violation
  fails the whole load.
- Duplicate detection compares subjects, so `Exception` and `exception`
  collide (folded kind) while `TRUE` and `true` do not (sensitive kind).
- `index.txt` lists relative document paths, one per line, sorted; blank
  lines and `#` comments are skipped; a path listed twice fails the load
  (commons-phpmodels rule).
- The bundled `vocabulary.yaml` declares every name `VulnType` and
  `SourceKind` enumerate, and no other; the psalm mapping lists every kind the
  two psalm-named sets use.

## Open Gaps

- `E_ALL`, `T_ABSTRACT`, `T_STRING`, `T_VARIABLE`, `T_LNUMBER`, `T_DNUMBER`,
  `FILTER_VALIDATE_MAC` and `OPENSSL_ALGO_MD5` are declared with values that
  differ from PHP 8.5.12 (`E_ALL` 32767 against 30719, `FILTER_VALIDATE_MAC`
  281 against 276, `OPENSSL_ALGO_MD5` 4 against 2); the cause (PHP version or
  declaration error) is not established.
- The models declare 242 of the 3025 constants PHP 8.5.12 defines (extension constants such as `FILEINFO_*`,
  `LIBXML_*` and `SOAP_*` among the missing ones; `CURLOPT_URL`, `SEEK_SET` and `LOCK_EX` are declared). A call
  with an undeclared constant as an argument is reported by no sink, so `new finfo(FILEINFO_NONE, $_GET['m'])` and
  `new SimpleXMLElement($_GET['u'], LIBXML_NOENT, true)` report nothing while the same calls with the literal flag
  report their constructor sink.
- Builtins that send a request for the URL in an argument on PHP 8.5.12 and carry no `ssrf` in `sinks.yaml`, so a
  program passing a request value to them reports nothing: `Dom\XMLDocument::createFromFile`,
  `Dom\Document::schemaValidate` and `Dom\Document::relaxNgValidate` (the PHP manual documents no method of
  `Dom\Document` or `Dom\XMLDocument`, so the second source is missing). Not run, because the extension
  is absent or the call needs a service:
  `yaml_parse_file`, `yaml_parse_url`, `ldap_connect`, the `http_*` and `swoole` request functions and the other
  builtins of `models/` whose `filename`, `uri` or `url` parameter reads or fetches.
- `PHP_FLOAT_INF`, `PHP_FLOAT_NAN`, `ARRAY_UNIQUE_REGULAR` and the
  `PDO_FETCH_*` constants are declared, but PHP 8.5.12 defines none of them.
- The constant entries of `core.yaml` come from `tools/convert_stubs.py` over
  phpstorm-stubs, a tool this repository no longer holds (the three php-src
  tools write no constant), so the 24 value-less constants were removed from
  `core.yaml` by hand and a regeneration with that tool would write them back.
  The producer has no exclusion of the subjects `manual/core.yaml` declares;
  the load failure and the test named above are the only guard.
