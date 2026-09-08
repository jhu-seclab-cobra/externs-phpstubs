# PHP Stubs — Lookup Design

Software structure of the Built-in Lookup: the merge over the bundled sets,
the record and fact types a consumer reads, and the `PhpStubs` facade.
Domain semantics: [model-lookup.md](model-lookup.md). Fold algorithm:
[spec-merge.md](spec-merge.md). Resource roots and set layouts:
[design.md](design.md).

## Design Overview

- **Classes:** `PhpStubs` (final class; companion delegates to the bundled
  instance), `BuiltinRecord<S>` (data class), `SinkFact`, `SourceFact`,
  `SanitizerFact`, `FlowFact`, `ReturnsFact` (data classes), `VulnClass`
  and `Origin` (enums), `Merge` (internal), `Mount` (internal data class)
- **Abstract:** `BuiltinLookup` (interface: every read of one merge),
  `Fact` (sealed interface)
- **External types (commons-phpmodels):** `DocumentSetLoader`,
  `DocumentSet`, `ResourceOpener`, `CategoryMappingLoader`,
  `CategoryMapping`, `ModelEntry`, `ModelSubject` and its seven subtypes,
  `ArgPattern`, `SignatureInfo` and its four subtypes, `SinkDecl`,
  `SourceDecl`, `SanitizerDecl`, `Propagation`, `ReturnKind`, `Vocabulary`,
  `TaintPolicy`, `VulnClassId`, `OriginId`, `Precedence`, `Verification`
- **Relationships:** `PhpStubs` holds one `Merge`; `Merge` folds `Mount`s
  (one per set, in Merge Order) into records; a `BuiltinRecord` owns its
  `Fact`s; every `Fact` names its owner subject and its condition. The
  companion holds the bundled `PhpStubs`; `with` builds a second one from
  the bundled mounts plus extension mounts. All arrows one-way into the
  format library.
- **Exceptions:** [design.md](design.md) Exception / Error Types.
- **Dependency roles:** Facade: `PhpStubs`. Contract: `BuiltinLookup`.
  Aggregate: `Merge`. Data holders: `BuiltinRecord`, the facts, `Mount`.
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

**Members** (all reads of a frozen merge; no lazy work after construction):

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
| `sinks`, `sources`, `sanitizers`, `flows`, `returns` | `List<…Fact>` | every fact of the kind over every record, load order |
| `vocabulary` | `Vocabulary` | accumulated over every mounted set |
| `policy` | `TaintPolicy` | accumulated over every mounted set |

A name that is not a PHP spelling of the kind is the format library's
`IllegalArgumentException`; an absent subject is `null`. No suffix, prefix,
or case-folded index exists: a looser match is the consumer's filter over an
enumeration.

### PhpStubs (final class)

**Responsibility:** One `BuiltinLookup` over one `Merge`, plus the
construction of merges. The bundled merge is built once when the class
initializes and shared; every extension merge is a new instance.

**Constructor (private):** `PhpStubs(merge: Merge)`.

**Companion:** `companion object : BuiltinLookup by bundled`, where
`bundled` is `PhpStubs(Merge.of(BUNDLED_MOUNTS))`; the four bundled mounts
are the constants of [design.md](design.md) Merge Order.

**Methods:**
- `fun with(vararg roots: String): PhpStubs` — classpath roots, each
  opened through `StubResources.opener`, mounted after this instance's
  mounts in the given order.
- `fun with(vararg dirs: Path): PhpStubs` — filesystem directories,
  opened relative to each directory, mounted the same way.
- `operator fun plus(root: String): PhpStubs`, `operator fun plus(dir: Path): PhpStubs`
  — `with` of one root.
- **Behavior:** every extension set decodes through
  `DocumentSetLoader.load(opener, vocabulary, mapping = null)` against the
  vocabulary accumulated so far; a set without `provenance.yaml` mounts as
  `Verification.MANUAL`. The receiver is unchanged.
- **Errors:** `StubIndexNotFoundException` (absent manifest or document),
  `StubIndexInvalidException` (any other set-load failure, cause attached).

### Mount (internal data class)

**Responsibility:** One set as mounted: its position in Merge Order, its
verification, and its documents, each document paired with the extension
its path yields (`.yaml` removed, trailing `_<digits>` removed) for the
generated set and `null` for every other set.

**State/Fields:** `position: Int`, `verification: Verification`,
`entries: List<Pair<ModelEntry, String?>>`.

### Merge (internal class)

**Responsibility:** The fold of [spec-merge.md](spec-merge.md) and the
records built from its result. Built once per set sequence, immutable.

**State/Fields:** `vocabulary`, `policy`, one `LinkedHashMap<Subject, BuiltinRecord>`
per declaration kind in first-statement order, and the five fact lists in
record order.

**Construction (`Merge.of(mounts: List<Mount>)`):** for each mount in
position order and each entry: key = (subject, condition); per unit the
entry declares, the statement in force is replaced when the new statement's
verification ranks at least equal under `Precedence.DEFAULT` (equal rank,
later position wins; lower rank never replaces). The extension of a record
is the extension of the statement in force for its signature unit. A
conditional entry declaring a signature is `StubIndexInvalidException`.

**Record assembly:** per subject, the signature is the unconditional
signature statement or `null`; the facts are every element of every
statement in force under every condition of that subject, each tagged with
its condition. Statement order within a subject is condition
first-statement order; element order is document order.

### BuiltinRecord<S : ModelSubject> (data class)

**Responsibility:** The one thing a consumer reads about a built-in.

**State/Fields:** `subject: S`, `extension: String?`,
`signature: SignatureInfo?`, `returns: List<ReturnsFact>`,
`flows: List<FlowFact>`, `sources: List<SourceFact>`, `sinks: List<SinkFact>`,
`sanitizers: List<SanitizerFact>`.

**Validation (`init`):** every fact's `owner == subject`; at least one of
`signature` or a fact present.

**Typed signature accessors** (extension properties, one per declaration
kind, narrowing `signature` and `null` when absent):
`BuiltinRecord<FunctionSubject>.callableSignature`,
`BuiltinRecord<MethodSubject>.callableSignature`,
`BuiltinRecord<ClassSubject>.classSignature`,
`BuiltinRecord<ConstantSubject>.typedSignature`,
`BuiltinRecord<ClassConstantSubject>.typedSignature`,
`BuiltinRecord<PropertySubject>.propertySignature`. The format library
already rejects a signature subtype that does not match the subject kind.

### Fact (sealed interface) and its five data classes

**Responsibility:** One element of one assertion statement, with the record
it belongs to and the condition it holds under. A consumer matches
`condition` against its own call arguments through `ArgPattern.matches` and
applies its own rule to an undecidable outcome; the library ranks nothing.

**Common fields:** `owner: ModelSubject`, `condition: ArgPattern?` (`null`
for an unconditional statement).

| Type | Own fields | From |
|------|------------|------|
| `SinkFact` | `port: Port.Argument`, `vulnClass: VulnClassId` | one `SinkDecl` |
| `SourceFact` | `origins: Set<OriginId>`, `at: Port.Argument?`, `keys: List<KeyPattern>?` | one `SourceDecl` |
| `SanitizerFact` | `categories: Set<VulnClassId>` | one `SanitizerDecl` |
| `FlowFact` | `from: Port.Input`, `to: Port` | one `Propagation` |
| `ReturnsFact` | `kind: ReturnKind` | the `returns` section |

### VulnClass, Origin (enums)

**Responsibility:** Compile-time names for the Canonical Vocabulary so a
consumer filters without spelling a string: `VulnClass.SQLI.id` is
`VulnClassId("sqli")`; `Origin.USER_INPUT.id` is `OriginId("user-input")`.
Twelve and two constants, each holding its `id`. A repository test asserts
the bundled vocabulary document declares exactly these names; a category an
extension set adds has no enum constant and is compared by `VulnClassId`.

## Validation Rules

- Existence of a declaration is `signature != null`; a record with facts
  and no signature (a taint-only function, every predefined variable) is a
  record all the same, so no fact is dropped by the merge.
- A category or color a fact carries is declared in `vocabulary`; the
  format library verified it when the set decoded.
- `functions.size` equals the number of distinct function subjects over
  every mounted set; a subject appears in exactly one kind map.
- Two `PhpStubs` built from equal mount lists hold equal records.
- No public type of this file holds a psalm name, a set root, a layer
  label, or a precedence.
