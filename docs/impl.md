# PHP Stubs Implementation Notes

## APIs

- **[commons-phpmodels]** (internal since 0.4.0; consumed through `DocumentSetLoader`) `ModelLoader.load(input: InputStream): List<ModelEntry>` — decodes one document; consumes and closes the stream; every format violation is `IllegalArgumentException` (message carries the reason, cause chain carries Jackson's location).
- **[commons-phpmodels 0.4.0]** `ModelEntry(subject, condition: ArgPattern?, signature: SignatureInfo?, body: ModelBody)` is the one entry data class; generators and `WhenGuard` are gone. `ArgPattern.expected: List<IPrimitiveVal?>`, `positions`, `matches(actual: List<IPrimitiveVal?>): Boolean?`; `ArgPattern` is a data class, so it keys a `Map` by value (the `(subject, condition)` merge key).
- **[commons-phpmodels 0.4.0]** `DocumentSetLoader.load(open, context, mapping)` and `CategoryMappingLoader.load(InputStream)` are the public loaders; `VocabularyLoader`, `PolicyLoader`, `ModelLoader`, `ProvenanceLoader` are internal. A set's verification is read from `DocumentSet.provenance?.verification`, never from a separate loader call. `DocumentSet.documents: List<Document(path, entries)>` keeps the manifest order the extension derivation needs.
- **[commons-phpmodels 0.4.0]** Renames consumed here: `SinkDecl(port, vulnClass)`, `SourceDecl(origin: Set<OriginId>, at, keys)`, `Vocabulary.origins`, `CategoryMapping.origins`; YAML keys unchanged.
- **[kotlin]** `companion object : BuiltinLookup by bundled` delegates only the interface members; `with`/`plus` are class members, so the companion declares its own `with`/`plus` forwarding to `bundled`. The delegate expression is evaluated when the companion initializes (first static access to `PhpStubs`), so `bundled` is a top-level `private val` of `PhpStubs.kt`, whose file class initializes on that first read. During that initialization the `Companion` static field is still null, so `bundled` must not touch any companion member, and a top-level value cannot call a private constructor: the constructor is `internal`. Verified 2026-09-08: a private constructor fails to compile, a companion reference from `bundled` throws `NullPointerException` at class init.
- **[commons-phpmodels]** `FunctionSubject.parse(raw)` / `ClassSubject.parse(raw)` / `ConstantSubject.parse(raw)` — strip one leading `\` only, then fold per kind; `IllegalArgumentException` on blank, whitespace, `::`, `$`. No `/` handling — PHP has no such separator.
- **[commons-phpmodels]** `MethodSubject(owner, name)` / `ClassConstantSubject(owner, name)` — direct constructors for a qualified lookup; `owner` folds, `name` folds for methods only.
- **[commons-phpmodels]** `ModelSubject.name` is declared on the sealed interface since v0.1.2; identity fields are still read through the concrete subtypes here.
- **[commons-phpmodels]** `SignatureInfo` subtypes: `CallableSignature(params, returnType)`, `ClassSignature(classifier, parent, interfaces)`, `TypedSignature(type, value)`, `PropertySignature(type, visibility, static)`; `ParameterInfo(name, type, optional, byRef, variadic)`. Field shape identical since v0.1.1; `ClassSignature` is built through its companion factory since v0.1.2 — read only, never construct.
- **[commons-phpmodels]** Entry-level validation since v0.1.2: arity against the parameter list unless the last parameter is variadic; by-ref write direction; `void` return with a return propagation; whitespace in identities; YAML aliases. v0.2.0 is the released HEAD, so a corpus that loads against the pin is proven against every rule.
- **[commons-phpmodels 0.3.0]** `DocumentSet.provenance: SetProvenance?` — `producer: String`, `verification: Verification` (`GENERATED`, `MANUAL`), read from the set's `provenance.yaml`; null when the file is absent. `Precedence.DEFAULT` ranks `MANUAL` above `GENERATED`; the fold is the consumer's.
- **[commons-phpmodels 0.5.0]** `ModelBody.raises: Set<ClassSubject>?` — `null` when the entry declares no raises section, the empty set for `raises: []`; each element decoded by the `ClassSubject` creator. Admitted on function and method entries only; the raises section is its own Override Unit and is not translated by a mapping. Declared types are kept as written (`?Throwable`, `int|string`), so a php-src type needs no simplification.
- **[commons-phpmodels 0.6.1]** `ModelBody.characters: CharacterBound?` — `CharacterBound(of: Set<Port.Argument>?, within: CharacterClass?)`, at least one field declared; each `of` port is the from-port of a declared flow into `Port.Return`. Part of the value-semantics unit: it requires returns and is served by `valueSemantics()`. `CharacterClass` rejects a pattern matching no byte; `contains(byte: Int)` reads the byte as one Latin-1 character and rejects a value outside 0..255. An argument's bytes are those of the strings the call converts it to.
- **[JDK]** `Class.getResourceAsStream(path)` — resolves `index.txt` and documents from the classpath; null when absent → `StubIndexNotFoundException`.

## Libraries

- com.github.jhu-seclab-cobra:commons-phpmodels:0.6.1 — model format, decoder, validation, condition match; `api` scope (its types are the record surface); commons-value 0.1.1 arrives transitively as its `api` dependency, so `ArgPattern` values are readable here without a direct declaration (the catalog alias `cobra-commons-value` is kept at 0.1.1 for the test that builds argument lists); alias `cobra-commons-phpmodels` in `gradle/libs.versions.toml`; resolved from JitPack (`https://jitpack.io`, artifact verified present) standalone, substituted by the enclosing composite build when one includes this repository.
- Jackson stays transitive and hidden: commons-phpmodels declares it `implementation`; no YAML library is declared here.

## Developer Instructions

- Corpus probe (2026-09-01): all 58 generated documents decode against commons-phpmodels HEAD, 5,680 entries (5,327 functions, 108 classes, 2 methods, 242 constants, 1 class constant).
- `index.txt` under `models/`, `taint/`, `taint-rules/`, `value-rules/` and `models-test/` is written by Gradle `processResources` / `processTestResources`; `vocabulary/index.txt` and every other test fixture directory keep a hand-written manifest.
- Generated documents (`models/**` except `models/language/` and `models/manual/`) are never hand-edited; a correction belongs in `value-rules/`, `taint-rules/`, or an extension set.
- Generated documents carry no language-construct subject: the keyword document owns `echo`, `empty`, `eval`, `isset`, `print`, `unset`, and the loader's duplicate rule rejects a second declaration. The extraction pipeline excludes those names on its next run (removed from `standard_1/3/5/7.yaml` on 2026-09-01).
- `shell_exec` is a `standard` function, not a language construct; the former hardcoded keyword set listed it and the keyword document does not.
- Performance tests are excluded by default: `./gradlew test -Pperformance`.
- The enclosing composite build is the integration check against a consumer; the standalone build (`./gradlew build` in this repository) is the check against the released commons-phpmodels tag.
- Until the commons-phpmodels tag is published, the standalone build resolves the pin from the sibling checkout through an init script, run as `./gradlew -I <script> build`:
  `gradle.settingsEvaluated { includeBuild("../commons-phpmodels") { dependencySubstitution { substitute(module("com.github.jhu-seclab-cobra:commons-phpmodels")).using(project(":jhu-seclab-cobra-commons-phpmodels")) } } }`.
- The pin (v0.6.1) carries the one entry form, `ArgPattern`, the internal single-document loaders, the `(subject, condition)` duplicate rule, the raises section, and the characters section; the standalone JitPack build exercises the same guarantees as the root composite once the tag is published.
- Canonical vocabulary resources live under `src/main/resources/vocabulary/`; `provenance.yaml` names the producer `externs-phpstubs canonical vocabulary`.

## Design-Specific

### Extension provenance

- Derived at load from the document file name: `standard_3.yaml` → `standard`; `language/keyword.yaml` → `keyword`. The model format carries no extension field.
- Former synthetic extension spellings `Scalar` and `Core` (for class `exit`) become `scalar` and `keyword`, following the document names.

### Subject name spelling

- Subject names separate namespace parts with `\`; the subject creators treat `/` as an ordinary name character, so a consumer converts its own spelling before every facade lookup.

### Variadic tails in generated data

- The upstream tag data never stated variadic parameters; the generator marked the last parameter variadic when a declared flow index reached past the parameter list (`sprintf`, `array_merge`, `compact`). Without the mark, commons-phpmodels HEAD rejects the entry for arity.

### Taint document set
- Source release: vimeo/psalm 5.6.0 (`vendor/vimeo/psalm` of a dataset checkout; version from `vendor/composer/installed.json`). Psalm declares 15 taint kinds; the `ALL_INPUT` group enables 13 (not `user_secret`, `system_secret`).
- Psalm's sources are code, not data: only `$_GET`, `$_POST`, `$_COOKIE`, `$_REQUEST` are colored (`VariableFetchAnalyzer::taintVariable`); `$_SERVER` and `$_FILES` are not. `@psalm-taint-source input` appears on `Throwable`, `Exception`, and `Error` `getTraceAsString`/`__toString` only.
- `@psalm-taint-specialize` has no model counterpart and is dropped. The five conditional escapes on `filter_var` become conditional entries `when: [_, 257]` … `[_, 520]`.
- Method subjects in the set (`mysqli::query`, `mysqli_stmt::prepare`, ...) are psalm's data verbatim, not a projection onto the generated set; a subject the generated set lacks is merged all the same.
- **[taint rules set]** Sinks follow `sinks.json` of the Argus artifact (411 sinks, 12 vulnerability types); `SinkPoint` accepts argument ports only, so the receiver-triggered deserialization getters (Phar, SplFileInfo, DirectoryIterator families) are omitted. `TaintPolicy` unions rows sharing an origin, so the set's `input → [xpath]` row extends psalm's row at load.
- **[commons-phpmodels 0.2.1]** `DocumentSetException(path, detail, cause?)` now wraps a malformed listed document; `VocabularyException` names the document on an undeclared reference. `MountSequence` maps absence to `StubIndexNotFoundException` by recording which path the opener could not resolve.

### Set provenance

- Every shipped set carries `provenance.yaml`; the index task lists no set-level document (`vocabulary.yaml`, `policy.yaml`, `provenance.yaml`). `models/` and `taint/` are `generated`; `taint-rules/` and `value-rules/` are `manual`.

### Value rules set

- The set was built from 129 reviewed entries on 2026-09-07 by classifying each against `models/` (script kept out of the repository; the unit of a generated entry is its return type's kind with its propagation): 89 add a unit the generated entry lacks, 23 differ, 2 are conditional entries (`when: [_, true]`), 15 name subjects the corpus lacks.
- PHP manual review of the 23 differing entries kept 20 with a reason comment and dropped 3 whose generated unit the manual confirms: `crypt` (the salt is a prefix of the hash), `str_word_count` (array or int by format), `setlocale` (echoes the locale set).
- Corrected against the manual: `parse_str` and `header` return void (the flow into the result is removed; `parse_str` writes its by-reference result argument), `echo` has no result, `print` always returns 1, `mysqli_multi_query`, `mysqli_real_query`, `proc_nice`, `proc_terminate`, `register_tick_function` return bool, `proc_close` returns int.
- Corpus gaps hand-declared under `models/manual/`: `hebrevc`, `convert_cyr_string`, `money_format`, `each`, `mysql_query`, `create_function` (removed before php-src 8.5.11). Their reviewed unit is the declaration's signature and propagation; `create_function` declares no propagation because the format rejects an empty flow set.
- php-src 8.5.11 declares the former manual entries `str_decrement`, `str_increment`, `mysqli::query`, `mysqli::multi_query`, `mysqli::real_query`, `PDO::query`, `PDO::exec`, `SQLite3::query`, `SQLite3::exec`, `Exception::__construct`, `Error::__construct`, and `Error::getMessage`, so the signature extraction generates them and a manual entry would duplicate a generated subject. Each reviewed flow moved to the value rules set with the result kind of the PHP manual: query methods `any`, `mysqli::multi_query`, `mysqli::real_query`, `SQLite3::exec` `bool`, `str_decrement` and `str_increment` `str` (argument into result), `Error::getMessage` `str` (receiver into result), the constructors the message argument into the receiver.
- The set ships 124 entries in fourteen documents.
