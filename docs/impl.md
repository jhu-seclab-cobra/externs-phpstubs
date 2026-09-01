# PHP Stubs Implementation Notes

## APIs

- **[commons-phpmodels]** `ModelLoader.load(input: InputStream): List<ModelEntry>` — decodes one document; consumes and closes the stream; every format violation is `IllegalArgumentException` (message carries the reason, cause chain carries Jackson's location).
- **[commons-phpmodels]** `ModelEntry` is sealed: `SubjectModel(subject, guard, signature, body)` or `ModelGenerator`; route with an exhaustive `when`.
- **[commons-phpmodels]** `FunctionSubject.parse(raw)` / `ClassSubject.parse(raw)` / `ConstantSubject.parse(raw)` — strip one leading `\` only, then fold per kind; `IllegalArgumentException` on blank, whitespace, `::`, `$`. No `/` handling — PHP has no such separator.
- **[commons-phpmodels]** `MethodSubject(owner, name)` / `ClassConstantSubject(owner, name)` — direct constructors for a qualified lookup; `owner` folds, `name` folds for methods only.
- **[commons-phpmodels]** `ModelSubject.name` is declared on the sealed interface at HEAD but not in v0.1.1 — read identity fields through the concrete subtypes only, so the standalone build compiles against the released tag.
- **[commons-phpmodels]** `SignatureInfo` subtypes: `CallableSignature(params, returnType)`, `ClassSignature(classifier, parent, interfaces)`, `TypedSignature(type, value)`, `PropertySignature(type, visibility, static)`; `ParameterInfo(name, type, optional, byRef, variadic)`. Field shape identical in v0.1.1 and HEAD; `ClassSignature` construction differs (plain class vs factory) — read only, never construct.
- **[commons-phpmodels]** Entry-level validation at HEAD (v0.1.1+33): arity against the parameter list unless the last parameter is variadic; by-ref write direction; `void` return with a return propagation; whitespace in identities; YAML aliases. v0.1.1 has none of these — a corpus that loads against v0.1.1 is not proven against HEAD.
- **[JDK]** `Class.getResourceAsStream(path)` — resolves `index.txt` and documents from the classpath; null when absent → `StubIndexNotFoundException`.

## Libraries

- com.github.jhu-seclab-cobra:commons-phpmodels:0.1.1 — model format, decoder, validation; `api` scope (its types are the entry surface); alias `cobra-commons-phpmodels` in `gradle/libs.versions.toml`; resolved from JitPack (`https://jitpack.io`, artifact verified present) standalone, substituted by the root composite when built from CobraPHP.
- Jackson stays transitive and hidden: commons-phpmodels declares it `implementation`; no YAML library is declared here.

## Developer Instructions

- Corpus probe (2026-09-01): all 58 generated documents decode against commons-phpmodels HEAD, 5,680 entries (5,327 functions, 108 classes, 2 methods, 242 constants, 1 class constant).
- `index.txt` under `models/` and `models-test/` is written by Gradle `processResources` / `processTestResources`; every other test fixture directory keeps a hand-written manifest.
- Generated documents (`models/**` except `models/language/`) are never hand-edited; a correction belongs in a higher configuration layer of the consumer.
- Generated documents carry no language-construct subject: the keyword document owns `echo`, `empty`, `eval`, `isset`, `print`, `unset`, and the loader's duplicate rule rejects a second declaration. The extraction pipeline excludes those names on its next run (removed from `standard_1/3/5/7.yaml` on 2026-09-01).
- `shell_exec` is a `standard` function, not a language construct; the former hardcoded keyword set listed it and the keyword document does not.
- Performance tests are excluded by default: `./gradlew test -Pperformance`.
- Composite root build is the integration check for cobraphp-core; the standalone build (`./gradlew build` in this repository) is the check against the released commons-phpmodels tag.
- A commons-phpmodels release carrying the HEAD validations (v0.1.2) is required before the declared version can be raised; until then the composite build is the only path exercising the stricter guarantees.

## Design-Specific

### Extension provenance

- Derived at load from the document file name: `standard_3.yaml` → `standard`; `language/keyword.yaml` → `keyword`. The model format carries no extension field.
- Former synthetic extension spellings `Scalar` and `Core` (for class `exit`) become `scalar` and `keyword`, following the document names.

### Consumer name spelling

- cobraphp-core spells namespaces with `/` (`Qualified`); `BuiltinExt` joins the parts with `\` before every facade lookup, since the subject creators treat `/` as an ordinary name character.

### Variadic tails in generated data

- The upstream tag data never stated variadic parameters; the generator marked the last parameter variadic when a declared flow index reached past the parameter list (`sprintf`, `array_merge`, `compact`). Without the mark, commons-phpmodels HEAD rejects the entry for arity.
