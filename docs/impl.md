# PHP Stubs — External APIs and developer instructions

## APIs

- **[commons-phpmodels]** `DocumentSetLoader.load(open, context, mapping)` — public set loader; the result preserves manifest document order; `VocabularyMappingLoader.load(InputStream)` reads a total mapping.
- **[commons-phpmodels]** `ModelEntry(subject, condition, signature, body)` — the single Model representation; `ArgPattern.matches(actual: List<IPrimitiveVal?>): Boolean?` returns null when undecidable and patterns have value equality.
- **[commons-phpmodels]** `ModelSubject.name` — identity fields are read through concrete subject types; creators remove one leading `\` and apply the dependency’s [identity rules](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/model-declarations.md#subject-kinds).
- **[commons-phpmodels]** `MethodSubject(owner, name)` and `ClassConstantSubject(owner, name)` — owner names fold ASCII case; method names fold, class-constant names retain case.
- **[commons-phpmodels]** `SignatureInfo` — callable, class, typed and property shapes and their validation are defined by [declaration types](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/design-declarations.md#signatureinfo-sealed); declared unions are retained.
- **[commons-phpmodels]** `DocumentSet.provenance?.verification` — GENERATED or MANUAL when provenance exists; `Precedence.DEFAULT.rank` is zero for MANUAL and one for GENERATED.
- **[commons-phpmodels]** `ModelBody.throws` — absent means no assertion; the empty set asserts no exceptions within the format’s boundary; this library’s incompleteness remains in [extraction gaps](design-extraction.md#open-gaps).
- **[commons-phpmodels]** `ModelBody.characters` and `valueUnit()` — the character bound belongs to the exhaustive Value unit; its definition and constraints are the [format model](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/model.md).
- **[commons-phpmodels]** `ArgumentCheck(argument, accepts, within, types)` — binds a result test to an accepted argument; translation retains an explicit type/character check even when all its vulnerability names are discarded.
- **[commons-phpmodels]** `DocumentSetException(path, detail, cause)` — a listed document load failure retains its path; an unlisted mapping name raises `VocabularyException` rather than being discarded.
- **[Kotlin]** `companion object : BuiltinLookup by bundled` — delegation covers interface members; class construction helpers forward explicitly. The top-level bundled value must not access the companion during its initialization, and its constructor is internal.
- **[JDK]** `Class.getResourceAsStream(path)` — an absent classpath resource returns null; the mount reader records absences to classify failures.
- **[SnakeYAML]** `Yaml(SafeConstructor(LoaderOptions()))` — the library catalog reader rejects duplicate and unexpected fields through its typed decoder; Model decoding remains in commons-phpmodels.

## Libraries

- `com.github.jhu-seclab-cobra:commons-phpmodels:56feb9d33a3cf8445eb74f01eb22279ed71f5674` — API dependency for Models, Signatures, Conditions and decoding; alias `cobra-commons-phpmodels` in `gradle/libs.versions.toml`.
- `org.yaml:snakeyaml:2.7` — implementation dependency for catalog decoding; alias `snakeyaml`.
- `com.github.jhu-seclab-cobra:commons-value` — transitive API dependency supplying Condition values; this module does not declare it directly.

## Developer instructions

- Gradle resource tasks generate manifests for `models/`, `taint/`, `taint-rules/`, `value-rules/`, `models-test/` and selectable Library Set roots; set-level vocabulary, policy, provenance and mapping files are not model-manifest entries.
- Edit manual rules; regenerate generated documents through their producer. `models/language/` and `models/manual/` remain hand-declared.
- Run `python3 -B -m unittest discover -s tools -p "test_*.py"` for producer changes.
- Run hierarchy, signature and throws extractors in that order with `--php-src <source-root> --models <isolated-models-copy>`; a second sequence must preserve byte identity, protected inputs and source hashes.
- Verify complete source-site dispositions and strict decoding after regeneration; [handler extraction](spec-extraction-handlers.md) owns source mapping.
- Run standalone `./gradlew build` against the catalog’s dependency pin; a composite build substitutes its checked-out dependencies and is a distinct integration check.
- Run composite model/stubs test and detekt tasks when changing extraction or decoding; include the named-extra and one-opcode tests specified in [signature extraction design](design-extraction-signatures.md).
- Run `./gradlew test -Pperformance` for tagged performance measurements; the default test task excludes them.
- Run `python3 -I tools/import_library.py --upstreams <directory> --check` to compare regenerated library resources, notices and rejection data.

## Design-specific

### Source extraction

- [Signature extraction](spec-extraction-signatures.md) owns compiler body admission, native argument reception, scalar defaults, frameless/special arities and named-extra policies.
- [Handler design](design-extraction-handlers.md) owns shared C reading, lexical bindings, memory effects, continuation checkpoints and source-established call-context APIs.
- `models/language/keyword.yaml` owns `echo`, `empty`, `eval`, `isset`, `print`, and `unset`; generated extraction excludes those subjects. `shell_exec` belongs to `standard`.

### Taint and Value units

- The generated taint input declares Psalm’s own kinds and its input policy; the manual taint set supplies its explicit vocabulary additions and assertions. Translation and resource ownership are specified in [taint design](design-taint.md) and [manual taint design](design-taint-rules.md).
- `filter_var` has five conditional sanitizer Facts and no unconditional one; a Condition is matched by the caller, never by the record.
- Receiver-triggered metadata deserialization is excluded from argument-port sink data; the resource header and [rationale](concept-taint-rules.md#rationale-and-rejected-alternatives) retain the reason.
- Removed language functions declared manually are `hebrevc`, `convert_cyr_string`, `money_format`, `each`, `mysql_query` and `create_function`; `create_function` declares no propagation when the format cannot state an empty set.
- A reviewed Value unit replaces the generated unit whole. Layout and subject/shape checks are specified in [value rules](design-value-rules.md).
- PHP extension derivation and platform-dependent constants are specified in [resource design](design.md); callers do not synthesize a constant value from the host running the analyzer.
