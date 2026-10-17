# PHP Stubs — Lookup Design

Software structure of `BuiltinLookup`: the merge over the bundled sets,
the record and fact types a consumer reads, and the `PhpStubs` facade.
Domain semantics: [model-lookup.md](model-lookup.md). Mount and merge
types: [design-merge.md](design-merge.md). Fold algorithm:
[spec-merge.md](spec-merge.md). Resource roots and set layouts:
[design.md](design.md).

## Design Overview

- **Classes:** `PhpStubs` (final class; companion delegates to the bundled
  instance), `BuiltinRecord<S>` (data class), `SinkFact`, `SourceFact`,
  `SanitizerFact`, `FlowFact`, `CharactersFact`, `ReturnsFact`, `ThrowsFact` (data classes),
  `VulnType` and `SourceKind` (enums); `SetMerge`, `Mount`, `MountSequence` (internal,
  [design-merge.md](design-merge.md))
- **Abstract:** `BuiltinLookup` (interface: every read of one merge),
  `Fact` (sealed interface)
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `ResourceOpener`, `VocabularyMappingLoader`,
  `VocabularyMapping`, `ModelEntry`, `ModelSubject` and its seven subtypes,
  `ArgPattern`, `SignatureInfo` and its four subtypes, `SinkDecl`,
  `SourceDecl`, `SanitizerDecl`, `ArgumentCheck`, `Propagation`, `CharacterClass`,
  `ReturnKind`, `Vocabulary`, `TaintPolicy`, `VulnTypeId`, `SourceKindId`, `Precedence`, `Verification`
- **Relationships:** `PhpStubs` holds one `SetMerge`; `SetMerge` folds `Mount`s
  (one per set, in Mount Order) into records; a `BuiltinRecord` owns its
  `Fact`s; every `Fact` names its owner subject and its condition. The
  companion holds the bundled `PhpStubs`; `with` builds a second one from
  the bundled mounts plus consumer set mounts. All arrows one-way into the
  format library.
- **Exceptions:** [design.md](design.md) Exception / Error Types.
- **Dependency roles:** Facade: `PhpStubs`. Contract: `BuiltinLookup`.
  Aggregate: `SetMerge`. Data holders: `BuiltinRecord`, the facts.
  Decoder and validator: commons-phpmodels.

Package `edu.jhu.cobra.externs.phpstubs`, `explicitApi()`. commons-phpmodels
stays an `api` dependency; commons-value is reached through it (`ArgPattern`
holds `IPrimitiveVal`) and is not declared here.

## Class / Type Specifications

### BuiltinLookup (interface)

**Responsibility:** The read surface of one merge: exact lookup per
declaration kind, enumeration per declaration kind and per fact kind, the
accumulated vocabulary and policy. Implemented by `PhpStubs` and, by
delegation, by its companion, so `PhpStubs.function("substr")` and
`PhpStubs.with(dir).function("substr")` are the same call on two merges.

**Members** (reads of a built merge; the seven fact lists are built on first read):

| Member | Return | Behavior |
|--------|--------|----------|
| `function(name)` | `BuiltinRecord<FunctionSubject>?` | `FunctionSubject.parse(name)`, map read |
| `clazz(name)` | `BuiltinRecord<ClassSubject>?` | `ClassSubject.parse(name)`, map read |
| `method(spelling)` / `method(owner, name)` | `BuiltinRecord<MethodSubject>?` | `MethodSubject.parse` / constructor, map read |
| `constant(name)` | `BuiltinRecord<ConstantSubject>?` | `ConstantSubject.parse(name)`, map read |
| `classConstant(spelling)` / `classConstant(owner, name)` | `BuiltinRecord<ClassConstantSubject>?` | parse / constructor, map read |
| `property(spelling)` / `property(owner, name)` | `BuiltinRecord<PropertySubject>?` | parse / constructor, map read |
| `variable(name)` | `BuiltinRecord<VariableSubject>?` | `VariableSubject.parse(name)`, map read |
| `record(subject)` | `BuiltinRecord<ModelSubject>?` | the record of an already built subject |
| `functions`, `classes`, `methods`, `constants`, `classConstants`, `properties`, `variables` | `Collection<BuiltinRecord<…>>` | every record of the kind, load order |
| `sinkFacts`, `sourceFacts`, `sanitizerFacts`, `flows`, `returns`, `throws` | `List<…Fact>` | every fact of the kind over every record, load order |
| `vocabulary` | `Vocabulary` | accumulated over every mounted set |
| `policy` | `TaintPolicy` | accumulated over every mounted set |

A name that is not a PHP spelling of the kind is the format library's
`IllegalArgumentException`; an absent subject is `null`. No suffix, prefix,
or case-folded index exists: a looser match is the consumer's filter over an
enumeration.

### PhpStubs (final class)

**Responsibility:** One `BuiltinLookup` over one `SetMerge`, plus the
construction of merges. The bundled merge is built once when the class
initializes and shared; every extension merge is a new instance.

**Constructor (internal):** `PhpStubs(mounts: List<Mount>)`; the instance
holds its mounts (so `with` can extend them) and `SetMerge.of(mounts)`.

**Companion:** `companion object : BuiltinLookup by bundled`, where
`bundled` is a top-level private `PhpStubs` over the mounts a
`MountSequence` builds in [design.md](design.md) Mount Order (the psalm
mapping read once from `StubResources.PSALM_MAPPING`). The constructor is
internal, not private, because a top-level value cannot call a private
constructor, and the companion cannot be referenced during its own
initialization ([impl.md](impl.md)). The companion declares `with`/`plus`
overloads forwarding to `bundled`, since delegation covers interface
members only.

**Methods:**
- `fun with(vararg roots: String): PhpStubs` — classpath roots, each
  opened through `StubResources.opener`, mounted after this instance's
  mounts in the given order.
- `fun with(vararg dirs: Path): PhpStubs` — filesystem directories,
  opened relative to each directory, mounted the same way.
- `operator fun plus(root: String): PhpStubs`, `operator fun plus(dir: Path): PhpStubs`
  — `with` of one root.
- **Behavior:** every consumer set decodes through
  `DocumentSetLoader.load(opener, vocabulary, mapping = null)` against the
  vocabulary accumulated so far; a set without `provenance.yaml` mounts as
  `Verification.MANUAL`. The receiver is unchanged.
- **Errors:** `StubIndexNotFoundException` (absent manifest or document),
  `StubIndexInvalidException` (any other set-load failure, cause attached).

### BuiltinRecord<S : ModelSubject> (data class)

**Responsibility:** The one thing a consumer reads about a builtin.

**State/Fields:** `subject: S`, `extension: String?`,
`signature: SignatureInfo?`, `returns: List<ReturnsFact>`,
`flows: List<FlowFact>`, `characters: List<CharactersFact>`,
`sourceFacts: List<SourceFact>`, `sinkFacts: List<SinkFact>`,
`sanitizerFacts: List<SanitizerFact>`, `throws: List<ThrowsFact>`.

**Validation (`init`):** every fact's `owner == subject`; at least one of
`signature` or a fact present.

### Fact (sealed interface) and its seven data classes

**Responsibility:** One element of one assertion unit of an entry in force, with the record
it belongs to and the condition it holds under. A consumer matches
`condition` against its own call arguments through `ArgPattern.matches` and
applies its own rule to an undecidable outcome; the library ranks nothing.

**Common fields:** `owner: ModelSubject`, `condition: ArgPattern?` (`null`
for an unconditional entry).

| Type | Own fields | From |
|------|------------|------|
| `SinkFact` | `port: Port.Argument`, `vulnType: VulnTypeId` | one `SinkDecl` |
| `SourceFact` | `sourceKinds: Set<SourceKindId>`, `at: Port.Argument?`, `keys: List<KeyPattern>?` | one `SourceDecl` |
| `SanitizerFact` | `vulnTypes: Set<VulnTypeId>`, `check: ArgumentCheck?` | one `SanitizerDecl` |
| `FlowFact` | `from: Port.Input`, `to: Port` | one `Propagation` |
| `CharactersFact` | `bound: CharacterBound` | the `characters` section, whole: the bytes the result may hold; the bound keeps its at-least-one-field invariant |
| `ReturnsFact` | `kind: ReturnKind` | the `returns` section |
| `ThrowsFact` | `classes: Set<ClassSubject>` | the `throws` section, whole: the empty set states the subject throws none |

### VulnType, SourceKind (enums)

**Responsibility:** Compile-time names for the Canonical Vocabulary so a
consumer filters without spelling a string: `VulnType.SQLI.id` is
`VulnTypeId("sqli")`; `SourceKind.USER_INPUT.id` is `SourceKindId("user-input")`.
Twelve and two constants, each holding its `id`. A repository test asserts
the bundled vocabulary document declares exactly these names; a vulnerability
type a consumer set adds has no enum constant and is compared by `VulnTypeId`.

## Function Specifications

Typed signature accessors: top-level extension properties, one per
declaration kind, narrowing `BuiltinRecord.signature` and `null` when absent:
`BuiltinRecord<FunctionSubject>.callableSignature`,
`BuiltinRecord<MethodSubject>.callableSignature`,
`BuiltinRecord<ClassSubject>.classSignature`,
`BuiltinRecord<ConstantSubject>.typedSignature`,
`BuiltinRecord<ClassConstantSubject>.typedSignature`,
`BuiltinRecord<PropertySubject>.propertySignature`. The format library
already rejects a signature subtype that does not match the subject kind.

## Validation Rules

- Existence of a declaration is `signature != null`; a record with facts
  and no signature (a taint-only function, every predefined variable) is a
  record all the same, so no fact is dropped by the merge.
- A vulnerability type or source kind a fact carries is declared in `vocabulary`; the
  format library verified it when the set decoded.
- `functions.size` equals the number of distinct function subjects over
  every mounted set; a subject appears in exactly one kind map.
- Two `PhpStubs` built from equal mount lists hold equal records.
- No public type of this file holds a psalm name, a set root, or a
  precedence.
