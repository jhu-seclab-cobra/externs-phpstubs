# PHP Stubs Implementation Notes

## APIs

- **[commons-phpmodels]** `ModelLoader.load(input: InputStream): List<ModelEntry>` — decodes one document; consumes and closes the stream; every format violation is `IllegalArgumentException` (message carries the reason, cause chain carries Jackson's location).
- **[commons-phpmodels 0.4.0]** `ModelEntry(subject, condition: ArgPattern?, signature: SignatureInfo?, body: ModelBody)` is the one entry data class; generators and `WhenGuard` are gone. `ArgPattern.expected: List<IPrimitiveVal?>`, `positions`, `matches(actual: List<IPrimitiveVal?>): Boolean?`; `ArgPattern` is a data class, so it keys a `Map` by value (the `(subject, condition)` merge key).
- **[commons-phpmodels 0.4.0]** `DocumentSetLoader.load(open, context, mapping)` and `CategoryMappingLoader.load(InputStream)` are the public loaders; `VocabularyLoader`, `PolicyLoader`, `ModelLoader`, `ProvenanceLoader` are internal. A set's verification is read from `DocumentSet.provenance?.verification`, never from a separate loader call. `DocumentSet.documents: List<Document(path, entries)>` keeps the manifest order the extension derivation needs.
- **[commons-phpmodels 0.4.0]** Renames consumed here: `SinkDecl(port, vulnClass)`, `SourceDecl(origin: Set<OriginId>, at, keys)`, `Vocabulary.origins`, `CategoryMapping.origins`; YAML keys unchanged.
- **[kotlin]** `companion object : BuiltinLookup by bundled` delegates only the interface members; `with`/`plus` are class members, so the companion declares its own `with`/`plus` forwarding to `bundled`. The delegate expression is evaluated when the companion initializes (first static access to `PhpStubs`), so `bundled` is a top-level `private val` of `PhpStubs.kt`, whose file class initializes on that first read.
- **[commons-phpmodels]** `FunctionSubject.parse(raw)` / `ClassSubject.parse(raw)` / `ConstantSubject.parse(raw)` — strip one leading `\` only, then fold per kind; `IllegalArgumentException` on blank, whitespace, `::`, `$`. No `/` handling — PHP has no such separator.
- **[commons-phpmodels]** `MethodSubject(owner, name)` / `ClassConstantSubject(owner, name)` — direct constructors for a qualified lookup; `owner` folds, `name` folds for methods only.
- **[commons-phpmodels]** `ModelSubject.name` is declared on the sealed interface since v0.1.2; identity fields are still read through the concrete subtypes here.
- **[commons-phpmodels]** `SignatureInfo` subtypes: `CallableSignature(params, returnType)`, `ClassSignature(classifier, parent, interfaces)`, `TypedSignature(type, value)`, `PropertySignature(type, visibility, static)`; `ParameterInfo(name, type, optional, byRef, variadic)`. Field shape identical since v0.1.1; `ClassSignature` is built through its companion factory since v0.1.2 — read only, never construct.
- **[commons-phpmodels]** Entry-level validation since v0.1.2: arity against the parameter list unless the last parameter is variadic; by-ref write direction; `void` return with a return propagation; whitespace in identities; YAML aliases. v0.2.0 is the released HEAD, so a corpus that loads against the pin is proven against every rule.
- **[commons-phpmodels 0.3.0]** `DocumentSet.provenance: SetProvenance?` — `producer: String`, `verification: Verification` (`GENERATED`, `MANUAL`), read from the set's `provenance.yaml`; null when the file is absent. `Precedence.DEFAULT` ranks `MANUAL` above `GENERATED`; the fold is the consumer's.
- **[JDK]** `Class.getResourceAsStream(path)` — resolves `index.txt` and documents from the classpath; null when absent → `StubIndexNotFoundException`.

## Libraries

- com.github.jhu-seclab-cobra:commons-phpmodels:0.4.0 — model format, decoder, validation, condition match; `api` scope (its types are the record surface); commons-value 0.1.1 arrives transitively as its `api` dependency, so `ArgPattern` values are readable here without a direct declaration (the catalog alias `cobra-commons-value` is kept at 0.1.1 for the test that builds argument lists); alias `cobra-commons-phpmodels` in `gradle/libs.versions.toml`; resolved from JitPack (`https://jitpack.io`, artifact verified present) standalone, substituted by the root composite when built from CobraPHP.
- Jackson stays transitive and hidden: commons-phpmodels declares it `implementation`; no YAML library is declared here.

## Developer Instructions

- Corpus probe (2026-09-01): all 58 generated documents decode against commons-phpmodels HEAD, 5,680 entries (5,327 functions, 108 classes, 2 methods, 242 constants, 1 class constant).
- `index.txt` under `models/` and `models-test/` is written by Gradle `processResources` / `processTestResources`; every other test fixture directory keeps a hand-written manifest.
- Generated documents (`models/**` except `models/language/` and `models/manual/`) are never hand-edited; a correction belongs in a higher configuration layer of the consumer.
- Generated documents carry no language-construct subject: the keyword document owns `echo`, `empty`, `eval`, `isset`, `print`, `unset`, and the loader's duplicate rule rejects a second declaration. The extraction pipeline excludes those names on its next run (removed from `standard_1/3/5/7.yaml` on 2026-09-01).
- `shell_exec` is a `standard` function, not a language construct; the former hardcoded keyword set listed it and the keyword document does not.
- Performance tests are excluded by default: `./gradlew test -Pperformance`.
- Composite root build is the integration check for cobraphp-core; the standalone build (`./gradlew build` in this repository) is the check against the released commons-phpmodels tag.
- The pin (v0.4.0) carries the one entry form, `ArgPattern`, the internal single-document loaders, and the `(subject, condition)` duplicate rule; the standalone JitPack build exercises the same guarantees as the root composite once the tag is published.
- Canonical vocabulary resources migrated from cobraphp-core `src/main/resources/vocabulary/` on 2026-09-08 unchanged in content; `provenance.yaml` producer renamed to `externs-phpstubs canonical vocabulary`.

## Design-Specific

### Extension provenance

- Derived at load from the document file name: `standard_3.yaml` → `standard`; `language/keyword.yaml` → `keyword`. The model format carries no extension field.
- Former synthetic extension spellings `Scalar` and `Core` (for class `exit`) become `scalar` and `keyword`, following the document names.

### Consumer name spelling

- cobraphp-core spells namespaces with `/` (`Qualified`); `BuiltinExt` joins the parts with `\` before every facade lookup, since the subject creators treat `/` as an ordinary name character.

### Variadic tails in generated data

- The upstream tag data never stated variadic parameters; the generator marked the last parameter variadic when a declared flow index reached past the parameter list (`sprintf`, `array_merge`, `compact`). Without the mark, commons-phpmodels HEAD rejects the entry for arity.

### Taint document set
- Source release: vimeo/psalm 5.6.0 (`vendor/vimeo/psalm` of a dataset checkout; version from `vendor/composer/installed.json`). Psalm declares 15 taint kinds; the `ALL_INPUT` group enables 13 (not `user_secret`, `system_secret`).
- Psalm's sources are code, not data: only `$_GET`, `$_POST`, `$_COOKIE`, `$_REQUEST` are colored (`VariableFetchAnalyzer::taintVariable`); `$_SERVER` and `$_FILES` are not. `@psalm-taint-source input` appears on `Throwable`, `Exception`, and `Error` `getTraceAsString`/`__toString` only.
- `@psalm-taint-specialize` has no model counterpart and is dropped. The five conditional escapes on `filter_var` become conditional entries `when: [_, 257]` … `[_, 520]`.
- Method subjects in the set (`mysqli::query`, `mysqli_stmt::prepare`, ...) are absent from the generated documents (the registry's methods are the generated `Exception` pair and the hand-declared `models/manual/` methods); the set is psalm's data verbatim, not a projection onto the registry.
- **[taint rules set]** Sinks follow `sinks.json` of the Argus artifact (411 sinks, 12 vulnerability types); `SinkPoint` accepts argument ports only, so the receiver-triggered deserialization getters (Phar, SplFileInfo, DirectoryIterator families) are omitted. `TaintPolicy` unions rows sharing an origin, so the set's `input → [xpath]` row extends psalm's row at load.
- **[commons-phpmodels 0.2.1]** `DocumentSetException(path, detail, cause?)` now wraps a malformed listed document; `VocabularyException` names the document on an undeclared reference. `StubLoader` maps absence to `StubIndexNotFoundException` by recording which path the opener could not resolve.

### Set provenance

- Every shipped set carries `provenance.yaml`; the index task lists no set-level document (`vocabulary.yaml`, `policy.yaml`, `provenance.yaml`). `models/` and `taint/` are `generated`; `taint-rules/` and `value-rules/` are `manual`.

### Value rules set

- Migrated from cobraphp-core's 129 rule entries on 2026-09-07 by classifying each against `models/` (script kept out of the repository; the unit of a generated entry is its return type's kind with its propagation): 89 add a unit the generated entry lacks, 23 differ, 2 are conditional entries (`when: [_, true]`), 15 name subjects the corpus lacks.
- PHP manual review of the 23 differing entries kept 20 with a reason comment and dropped 3 whose generated unit the manual confirms: `crypt` (the salt is a prefix of the hash), `str_word_count` (array or int by format), `setlocale` (echoes the locale set).
- Corrected against the manual: `parse_str` and `header` return void (the flow into the result is removed; `parse_str` writes its by-reference result argument), `echo` has no result, `print` always returns 1, `mysqli_multi_query`, `mysqli_real_query`, `proc_nice`, `proc_terminate`, `register_tick_function` return bool, `proc_close` returns int.
- Corpus gaps, excluded from the set and hand-declared under `models/manual/` on 2026-09-07 (todo.md T11): `str_decrement`, `str_increment` (PHP 8.3), `hebrevc`, `convert_cyr_string`, `money_format`, `each`, `mysql_query`, `create_function` (removed before the upstream release), and the methods `mysqli::query`, `mysqli::multi_query`, `mysqli::real_query`, `PDO::query`, `PDO::exec`, `SQLite3::query`, `SQLite3::exec` (the extraction emits no methods for these classes). Their reviewed unit is the declaration's signature and propagation; `create_function` declares no propagation because the format rejects an empty flow set.
- The set ships 111 entries in thirteen documents.
