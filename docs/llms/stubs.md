# Stubs API

> One record per PHP builtin over the merged document sets.

## Quick Start

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs
import edu.jhu.cobra.externs.phpstubs.VulnType
import edu.jhu.cobra.externs.phpstubs.callableSignature

val strlen = PhpStubs.function("strlen")                 // BuiltinRecord<FunctionSubject>?
strlen?.extension                                        // "core"
strlen?.callableSignature?.returnType                    // DeclaredType("int")
strlen?.returns?.single()?.kind                          // ReturnKind.NUM
val query = PhpStubs.method("mysqli::query")             // BuiltinRecord<MethodSubject>?
query?.sinkFacts?.single()?.vulnType == VulnType.SQLI.id   // true
```

## API

### BuiltinLookup (interface)

**Exact lookup** (PHP spelling; `IllegalArgumentException` for a non-spelling; `null` when absent):

**`function(name: String): BuiltinRecord<FunctionSubject>?`** -- Includes keyword constructs (`echo`, `isset`, ...; extension `keyword`).

**`clazz(name: String): BuiltinRecord<ClassSubject>?`** -- Includes scalar types (`int`, `float`, ...; extension `scalar`), `exit` (`keyword`), `resource` (`legacy`).

**`method(spelling: String)`**, **`method(owner: String, name: String): BuiltinRecord<MethodSubject>?`** -- `Owner::name`, or owner and name apart. Both halves fold.

**`constant(name: String): BuiltinRecord<ConstantSubject>?`** -- Global constants, case preserved.

**`classConstant(spelling: String)`**, **`classConstant(owner: String, name: String): BuiltinRecord<ClassConstantSubject>?`** -- `Owner::NAME`; the name keeps its case.

**`property(spelling: String)`**, **`property(owner: String, name: String): BuiltinRecord<PropertySubject>?`** -- `Owner::$name`.

**`variable(name: String): BuiltinRecord<VariableSubject>?`** -- `$name`; the bundled sets state `$_GET`, `$_POST`, `$_COOKIE`, `$_REQUEST`, `$_SERVER`, ... as source-only records.

**`record(subject: ModelSubject): BuiltinRecord<ModelSubject>?`** -- An already built subject.

**Enumeration** (records in Mount Order of each subject's first mounted entry; facts in record order, then condition, unit and document order):

**`functions`, `classes`, `methods`, `constants`, `classConstants`, `properties`, `variables`** -- `Collection<BuiltinRecord<…>>`.

**`sinkFacts: List<SinkFact>`**, **`sourceFacts: List<SourceFact>`**, **`sanitizerFacts: List<SanitizerFact>`**, **`flows: List<FlowFact>`**, **`characters: List<CharactersFact>`**, **`returns: List<ReturnsFact>`**, **`throws: List<ThrowsFact>`**.

**`vocabulary: Vocabulary`**, **`policy: TaintPolicy`** -- Accumulated over every mounted set; `policy.isDangerous(sourceKind, vulnType)`.

### PhpStubs (class, companion = bundled lookup)

**`PhpStubs.<any BuiltinLookup member>`** -- The bundled merge, built on first access and shared.

**`with(vararg roots: String): PhpStubs`**, **`with(vararg dirs: Path): PhpStubs`**, **`plus(root)`, `plus(dir)`** -- A new lookup mounting the consumer sets after this lookup's sets, in order; each decodes against the vocabulary accumulated so far; no `provenance.yaml` means manual. The receiver is unchanged. Also on the companion.

### BuiltinRecord<S : ModelSubject> (data class)

**`subject: S`**, **`extension: String?`** (from the generated document's placement, `standard_3.yaml` -> `standard`; `null` when no generated set declares the subject), **`signature: SignatureInfo?`** (the signature of the unconditional entry in force), **`returns`, `flows`, `characters`, `sourceFacts`, `sinkFacts`, `sanitizerFacts`, `throws`** (every fact in force under every condition), **`facts`** (all seven in that order). Construction requires a signature or at least one fact, and every fact's `owner == subject`.

Typed accessors (top-level extension properties, nullable):

**`BuiltinRecord<FunctionSubject>.callableSignature`**, **`BuiltinRecord<MethodSubject>.callableSignature`** -- `CallableSignature(params, returnType)`.

**`BuiltinRecord<ClassSubject>.classSignature`** -- `ClassSignature(classifier, parent, interfaces)`, folded.

**`BuiltinRecord<ConstantSubject>.typedSignature`**, **`BuiltinRecord<ClassConstantSubject>.typedSignature`** -- `TypedSignature(type, value)`.

**`BuiltinRecord<PropertySubject>.propertySignature`** -- `PropertySignature(type, visibility, static)`.

### Fact (sealed interface)

Every fact: **`owner: ModelSubject`**, **`condition: ArgPattern?`** (`null` for an unconditional entry; otherwise match it with `condition.matches(args)` -> `true`, `false`, or `null` for undecidable).

**`SinkFact(port: Port.Argument, vulnType: VulnTypeId)`** | **`SourceFact(sourceKinds: Set<SourceKindId>, at: Port.Argument?, keys: List<KeyPattern>?)`** | **`SanitizerFact(vulnTypes: Set<VulnTypeId>, check: ArgumentCheck?)`** | **`FlowFact(from: Port.Input, to: Port)`** | **`CharactersFact(bound: CharacterBound)`** | **`ReturnsFact(kind: ReturnKind)`** | **`ThrowsFact(classes: Set<ClassSubject>)`**.

### VulnType, SourceKind (enums)

**`VulnType.SQLI.id`** ... -- `VulnTypeId` per canonical vulnerability type: `sqli`, `cmdi`, `codei`, `xss`, `headeri`, `ssrf`, `pathtrav`, `fileinc`, `deser`, `callablei`, `ldapi`, `xpathi`, `schemei`. **`SourceKind.USER_INPUT.id`**, **`SourceKind.EXTERNAL_INPUT.id`**, **`SourceKind.SERVER_PATH.id`** -- `SourceKindId("user-input")`, `SourceKindId("external-input")`, `SourceKindId("server-path")`. A vulnerability type a consumer set adds has no constant.

### StubResources (object)

**`MODELS`** (`/models/`, generated set), **`VALUE_RULES`** (`/value-rules/`, manual value units), **`VOCABULARY`** (`/vocabulary/`, the canonical vocabulary and policy, manual), **`TAINT`** (`/taint/`, psalm's data in psalm's names, generated), **`TAINT_RULES`** (`/taint-rules/`, manual additions in psalm's names, adds `xpath` and `external`), **`PSALM_MAPPING`** (`/vocabulary/psalm-mapping.yaml`). Mount order is that listing. **`opener(root: String): ResourceOpener`** -- `root + path` on this module's classpath; trailing slash optional; `null` for an absent path.

```kotlin
val canonical = DocumentSetLoader.load(StubResources.opener(StubResources.VOCABULARY)).vocabulary
val mapping = StubResources::class.java.getResourceAsStream(StubResources.PSALM_MAPPING)!!.use(VocabularyMappingLoader::load)
val taint = DocumentSetLoader.load(StubResources.opener(StubResources.TAINT), canonical, mapping)
val values = DocumentSetLoader.load(StubResources.opener(StubResources.VALUE_RULES))
values.provenance?.verification                    // Verification.MANUAL
```

### Exceptions

**`StubIndexNotFoundException`** -- `index.txt` or a listed document is absent; the message names the resource path.

**`StubIndexInvalidException`** -- A set fails to decode (cause attached), a bundled set lacks `provenance.yaml`, a generated entry breaks a generated-set rule (variable subject, no signature, duplicate subject across documents), or a conditional entry declares a signature.

**`IllegalArgumentException`** -- A lookup name is not a PHP spelling of the kind; a `BuiltinRecord` is built empty or with a foreign fact.

## Gotchas

- Identity folding is commons-phpmodels': `MethodSubject("Exception", "getMessage")` equals `MethodSubject("exception", "getmessage")`; `ConstantSubject("TRUE")` and `ConstantSubject("true")` differ.
- No suffix, prefix, or case-folded index exists; a looser match is your filter over an enumeration.
- `strlen` and other value rules subjects carry the manual value unit (`returns: num`), not the generated one: manual outranks generated whatever the position.
- `filter_var` is five conditional sanitizer facts (`[_, 257]` ... `[_, 520]`) and no unconditional one; `print_r` and `var_export` carry a `[_, true]` returns fact beside the unconditional one. Choose per your undecidable rule.
- A value unit is `returns` plus the `flows` and `characters` of the same entry: filter both by equality with the chosen returns fact's `condition`.
- `throws` of a generated function or method is computed from the php-src C sources: an empty `classes` set states the call throws none; no `ThrowsFact` (`assert`, `Generator::throw`, entries outside php-src) asserts nothing. A class thrown only through a function pointer is missing.
- Constant values are strings on `typedSignature.value`; the consumer converts.
- Generated documents are never hand-edited; a correction belongs in `value-rules/` or `taint-rules/`, or in a consumer set mounted through `with`.
- Two lookups built from the same sets hold equal records, not the same instances.
