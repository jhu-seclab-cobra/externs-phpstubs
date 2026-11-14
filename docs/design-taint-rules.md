# PHP Stubs — Taint Rules Document Set Design

The classpath root and layout of the hand-maintained taint rules document set.
Concepts: [concept-taint-rules.md](concept-taint-rules.md). The opener and the taint
set: [design-taint.md](design-taint.md).

## Design Overview

- **Classes:** `StubResources` (object; the `TAINT_RULES` constant only)
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `VocabularyMapping`, `Vocabulary`
- **Relationships:** `PhpStubs` mounts the set at position 4 under
  `PSALM_MAPPING` against the accumulated canonical vocabulary
  ([design.md](design.md) mount order).
- **Exceptions:** none of its own.

## Class / Type Specifications

Resource roots and opener API: [StubResources](design.md#stubresources-object).

Source assertions: [@argus-artifact; @modern-php-security].

## Resource Layout

```
taint-rules/
├── index.txt          # build-generated manifest: sanitizers.yaml, sinks.yaml, sources.yaml
├── provenance.yaml    # producer externs-phpstubs review of Argus, the PHP manual and Synacktiv sec4dev 2020; verification manual
├── vocabulary.yaml    # kinds xpath, scheme; source kinds external, path
├── policy.yaml        # input gains xpath, scheme; external every input kind; path every external kind but scheme
├── sinks.yaml         # Argus, constructor, loader and stream-wrapper sinks; existing ports and kinds
├── sanitizers.yaml    # sanitizer facts psalm lacks: shell, html, sql, file, value-typing sanitizer facts for every kind; checks
└── sources.yaml       # `input` for request data psalm does not taint, `$_SERVER` split by key into `path` and `input`; `external` for environment and stored data
```

The canonical `schemei` declaration owns the HTML Tokenizer language. Its six
target states cover the leading URL position before a bare value or inside either
quote form, including an unfinished ASCII scheme name. The recognized attributes
are `href`, `src`, `action`, `formaction` and `xlink:href`. Only the format's byte
transition function is provided. The bundled sets declare no `scheme` sinks:
a consumer must read output context before those sinks can distinguish a leading
URL position from another use of the same bytes. Nested script, style and raw-text languages are outside this declaration.

Every document carries a header naming its provenance. Entry forms match
the taint set's table in [design-taint.md](design-taint.md). The conditional sink entry is `SimpleXMLElement::__construct`, `when: [_, _, true]`.
Digest sanitizers for `md5`, `sha1`, `hash` and `hash_hmac` require `binary` to be false,
including its omitted default. Entries are sorted by subject spelling.

| Document | Subject kinds | Content |
|----------|---------------|---------|
| sinks.yaml | function, method, operation | Argument sinks and the invocation selector, specified below |
| sanitizers.yaml | function | one declaration per subject; a value-typing sanitizer fact (`intval`, `md5`, ...) names every kind; a check names `argument(0)` and `accepts: true` with the `types` of a type predicate (`is_int`, `is_scalar`, ...) or the `within` class of a character check (`ctype_digit`, `is_numeric`, ...) with the kinds its class cannot carry |
| sources.yaml | variable, function, method | one declaration per subject producing `input`, `external` or `path`; `$_SERVER` holds two declarations split by `keys` |

## Sink declarations

Each row below states the dangerous input consumed by the builtin. Receiver-triggered sinks are omitted because an argument port does not identify a receiver. The invocation operation consumes `callee`. Path/URL readers use `ssrf` when PHP sends a request to the supplied URL, independent of whether raw bytes return; write-only paths gain no request sink.

| Builtins | Port | Kinds and condition |
|----------|------|---------------------|
| `finfo::__construct` | `argument(1)` | `file` |
| `SoapClient::__construct` | `argument(0)` | `ssrf` |
| `SimpleXMLElement::__construct` | `argument(0)` | `ssrf`, `file` when `dataIsURL` is true |
| `simplexml_load_file`, `tidy_parse_file`, `tidy_repair_file` | `argument(0)` | `ssrf`, `file` |
| `Dom\HTMLDocument::createFromFile`, `DOMDocument::load`, `DOMDocument::loadHTMLFile` | `argument(0)` | `ssrf`, `file` |
| `XMLReader::fromUri`, `XMLReader::open`, `tidy::__construct`, `tidy::parseFile`, `tidy::repairFile` | `argument(0)` | `ssrf`, `file` |
| `DOMDocument::schemaValidate`, `DOMDocument::relaxNGValidate` | `argument(0)` | `ssrf`; schema validation exposes content as validation/error output |
| `XMLReader::setSchema`, `XMLReader::setRelaxNGSchema`, `SoapServer::__construct` | `argument(0)` | `ssrf`; schema/WSDL content is not returned as raw bytes |

## Stream-Wrapper Readers

These file builtins read the path through stream wrappers. Their hand-maintained
entries contain `ssrf` and `file` on the port below, together with their other declared sink points.
Kinds use the taint set's spelling; the mapping exposes `file` as `pathtrav`.

| Builtins | Read port |
|----------|-----------|
| `exif_imagetype`, `exif_read_data`, `exif_thumbnail` | `argument(0)` |
| `hash_file`, `hash_hmac_file`, `hash_update_file` | `argument(1)` |
| `md5_file`, `sha1_file` | `argument(0)` |
| `gzfile`, `gzopen`, `bzopen`, `readgzfile` | `argument(0)` |
| `mime_content_type`, `finfo::file` | `argument(0)` |
| `finfo_file` | `argument(1)` |
| `imagecreatefromavif`, `imagecreatefrombmp`, `imagecreatefromgd`, `imagecreatefromgd2`, `imagecreatefromgd2part`, `imagecreatefromgif`, `imagecreatefromjpeg`, `imagecreatefrompng`, `imagecreatefromtga`, `imagecreatefromwbmp`, `imagecreatefromwebp`, `imagecreatefromxbm`, `imagecreatefromxpm`, `imageloadfont` | `argument(0)` |
| `file_get_contents`, `fopen`, `file`, `copy` | `argument(0)` |
| `get_meta_tags`, `getimagesize`, `highlight_file`, `show_source`, `parse_ini_file`, `php_strip_whitespace` | `argument(0)` |
| `SplFileObject::__construct` | `argument(0)` |

The write destination of `copy` retains `file` on `argument(1)`; it gains no `ssrf`.
`readgzfile` retains its `html` sink. `imagecreatefromstring` consumes bytes rather
than a path and is outside this rule. `readfile` already carries both path sinks.

## Validation Rules

- The set decodes over the taint set's vocabulary with no mapping and
  fails to decode alone: its vocabulary declares only the resource constants.
- Every entry declares no signature and exactly one of
  the three taint sections.
- No entry's section equals the taint set's section for the same subject
  and condition.
- A sinks entry whose subject the taint set also sinks contains every one
  of the taint set's sink points.
- A consumer's mapping lists every psalm kind, `xpath`, `scheme`, `input`,
  `external`, and `path`; an unlisted name is the format library's `VocabularyException`.
- The repository tests, not the consumer, prove the set decodes.

## Maintenance

The set is edited by hand. A new sink is one entry with all of its kinds;
a subject the taint set already sinks copies psalm's points before adding
its own. A new kind or source kind is declared in `vocabulary.yaml` and enabled
in `policy.yaml` before any document names it.

## Exception / Error Types

Set loading raises the errors specified in [the resource design](design.md#exception--error-types).
