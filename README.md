# COBRA.EXTERNS.PHPSTUBS

> PHP built-in lookup for static analysis: declarations, value semantics, and taint facts in one record per built-in.

Lookup of PHP built-in functions, classes, methods, constants, properties, and predefined variables by their PHP spelling. Each record merges the generated declarations (extension, signature), the hand-maintained value rules, psalm's taint data, and the hand-maintained taint rules into one `BuiltinRecord`: the signature in force plus every sink, source, sanitizer, flow, and returns fact, each tagged with the argument condition it holds under. Taint facts speak one canonical vocabulary; a consumer holds no set, mapping, or precedence.

[![codecov](https://codecov.io/gh/jhu-seclab-cobra/externs-phpstubs/branch/main/graph/badge.svg)](https://codecov.io/gh/jhu-seclab-cobra/externs-phpstubs)
![Kotlin JVM](https://img.shields.io/badge/Kotlin%20JVM-2.2.21%20%7C%20JVM%2021%2B-blue?logo=kotlin)
[![Release](https://img.shields.io/badge/release-v0.7.0-blue.svg)](https://github.com/jhu-seclab-cobra/externs-phpstubs/releases/tag/v0.7.0)
[![last commit](https://img.shields.io/github/last-commit/jhu-seclab-cobra/externs-phpstubs)](https://github.com/jhu-seclab-cobra/externs-phpstubs/commits/main)
[![](https://jitpack.io/v/jhu-seclab-cobra/externs-phpstubs.svg)](https://jitpack.io/#jhu-seclab-cobra/externs-phpstubs)
![Repo Size](https://img.shields.io/github/repo-size/jhu-seclab-cobra/externs-phpstubs)
[![license](https://img.shields.io/github/license/jhu-seclab-cobra/externs-phpstubs)](./LICENSE)

## Install

```kotlin
repositories {
    maven { url = uri("https://jitpack.io") }
}

dependencies {
    implementation("com.github.jhu-seclab-cobra:externs-phpstubs:0.7.0")
}
```

## Usage

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs
import edu.jhu.cobra.externs.phpstubs.VulnClass
import edu.jhu.cobra.externs.phpstubs.callableSignature
import edu.jhu.cobra.externs.phpstubs.typedSignature
import java.nio.file.Path

// One record per built-in: extension, signature, and every fact in force
val strlen = PhpStubs.function("strlen")
strlen?.extension                            // "standard"
strlen?.callableSignature?.returnType        // DeclaredType("int")
strlen?.returns?.single()?.kind              // ReturnKind.NUM (value rules outrank the generated unit)
strlen?.flows                                // [FlowFact(argument(0) -> return)]

// Taint facts in the canonical vocabulary, with their argument conditions
PhpStubs.method("mysqli::query")?.sinks      // [SinkFact(port = argument(0), vulnClass = sqli)]
PhpStubs.variable("\$_GET")?.sources         // [SourceFact(origins = {user-input})]
PhpStubs.function("filter_var")?.sanitizers  // five facts, each with condition [_, <FILTER_* id>]
    ?.filter { it.condition?.matches(myCallArguments) == true }

// Constants keep their case; a member spelling on a function lookup is an argument error
PhpStubs.constant("PHP_INT_MAX")?.typedSignature?.value    // "9223372036854775807"
PhpStubs.constant("php_int_max")                           // null
PhpStubs.classConstant("Exception::SEVERITY_ERROR")        // record

// Enumerations for a consumer's own filter
PhpStubs.sinks.filter { it.vulnClass == VulnClass.SQLI.id }
PhpStubs.functions.filter { it.extension == "keyword" }

// Extension sets mount after the bundled ones; the bundled lookup is unchanged
val extended = PhpStubs.with(Path.of("models/site-rules"))
```

## API

**`BuiltinLookup`** -- the read surface of one merge. Every exact lookup spells its subject in PHP's own grammar through the [commons-phpmodels](https://github.com/jhu-seclab-cobra/commons-phpmodels) subject creators: functions, classes, and methods fold case and drop a leading `\`; constants keep their case. A name that is not a spelling of the kind raises `IllegalArgumentException`; an absent subject is `null`.

| Member | Return |
|--------|--------|
| `function(name)` | `BuiltinRecord<FunctionSubject>?` |
| `clazz(name)` | `BuiltinRecord<ClassSubject>?` |
| `method(spelling)`, `method(owner, name)` | `BuiltinRecord<MethodSubject>?` |
| `constant(name)` | `BuiltinRecord<ConstantSubject>?` |
| `classConstant(spelling)`, `classConstant(owner, name)` | `BuiltinRecord<ClassConstantSubject>?` |
| `property(spelling)`, `property(owner, name)` | `BuiltinRecord<PropertySubject>?` |
| `variable(name)` | `BuiltinRecord<VariableSubject>?` |
| `record(subject)` | `BuiltinRecord<ModelSubject>?` |
| `functions`, `classes`, `methods`, `constants`, `classConstants`, `properties`, `variables` | `Collection<BuiltinRecord<…>>` in first-statement order |
| `sinks`, `sources`, `sanitizers`, `flows`, `returns` | `List<…Fact>` in record order |
| `vocabulary`, `policy` | `Vocabulary`, `TaintPolicy` accumulated over every mounted set |

**`PhpStubs`** -- one `BuiltinLookup` over one merge. The companion is the lookup over the bundled sets, built on first access and shared. `with(vararg roots: String)`, `with(vararg dirs: Path)`, and `plus` build a second lookup that mounts extension sets after the bundled ones, in order; a set without `provenance.yaml` mounts as manual.

**`BuiltinRecord<S>`** -- `(subject, extension: String?, signature: SignatureInfo?, returns, flows, sources, sinks, sanitizers)`. Typed accessors: `callableSignature` (function, method), `classSignature` (class), `typedSignature` (constant, class constant), `propertySignature` (property). `extension` is the PHP extension of the generated declaration, `null` for a subject only a hand-maintained set states.

**`Fact`** -- `SinkFact(port, vulnClass)`, `SourceFact(origins, at, keys)`, `SanitizerFact(categories)`, `FlowFact(from, to)`, `ReturnsFact(kind)`; each carries `owner` and `condition: ArgPattern?`. The record ranks nothing: a consumer matches each condition against its call arguments and applies its own rule to an undecidable outcome.

**`VulnClass`**, **`Origin`** -- enum constants for the canonical vocabulary (`sqli`, `cmdi`, `codei`, `xss`, `headeri`, `ssrf`, `pathtrav`, `fileinc`, `deser`, `callablei`, `ldapi`, `xpathi`; `user-input`, `external-input`).

**`StubResources`** -- classpath roots of the five bundled sets, `MODELS`, `VALUE_RULES`, `VOCABULARY`, `TAINT`, `TAINT_RULES`, the `PSALM_MAPPING` document, and `opener(root)`.

## Bundled Sets and Merge Order

| Position | Root | Content | Provenance |
|----------|------|---------|------------|
| 0 | `models/` | Generated declarations: signature per entry, extension from document placement | generated |
| 1 | `value-rules/` | Hand-maintained value semantics beyond or against the generated ones, checked against the PHP manual | manual |
| 2 | `vocabulary/` | The canonical danger categories, origin colors, and policy; the psalm mapping | manual |
| 3 | `taint/` | psalm's sinks, sanitizers, sources in psalm's names, translated by the psalm mapping | generated |
| 4 | `taint-rules/` | Hand-maintained sinks (Argus lists), escapes, and sources psalm lacks, translated by the same mapping | manual |

The merge keeps one statement per (subject, condition, unit); a higher-ranked provenance wins (`Precedence.DEFAULT`: manual over generated), and among equal ranks the later position wins. A unit is replaced whole; a set that omits a unit leaves the earlier statement in force. Each set also loads on its own through commons-phpmodels `DocumentSetLoader.load(StubResources.opener(root), context, mapping)`; the taint set is regenerated from a psalm checkout by `tools/extract_taint.py --psalm <root> --out externs-phpstubs/src/main/resources/taint`.

## Background

Model documents derived from [JetBrains/phpstorm-stubs](https://github.com/JetBrains/phpstorm-stubs) (signatures, Apache-2.0) and [vimeo/psalm](https://github.com/vimeo/psalm) (dataflow annotations and taint data, MIT), emitted in the [commons-phpmodels](https://github.com/jhu-seclab-cobra/commons-phpmodels) format. Language constructs (`echo`, `isset`, `int`, ...) are declared as data under `models/language/`; built-ins the extraction does not produce are hand-declared under `models/manual/`.

## Documentation

- [Concepts](docs/concept.md) -- generated layer over commons-phpmodels, extension provenance, lookup semantics
- [Lookup Concepts](docs/concept-lookup.md) -- canonical vocabulary, the merge, Built-in Record and Built-in Lookup
- [Lookup Model](docs/model-lookup.md) -- bundled sets, merge order, statements in force, records and facts
- [Merge Algorithm](docs/spec-merge.md) -- folding the mounted sets into one statement per subject, condition, and unit
- [Taint Concepts](docs/concept-taint.md) -- the taint document set in psalm's names and its extraction
- [Design](docs/design.md) -- resource roots, merge order, corpus rules, exception types
- [Lookup Design](docs/design-lookup.md) -- `BuiltinLookup`, `PhpStubs`, `BuiltinRecord`, fact types, canonical enums
- [Merge Design](docs/design-merge.md) -- `Mount`, `MountSequence`, `Merge`
- [Taint Design](docs/design-taint.md) -- `StubResources`, taint resource layout, extraction script
- [Taint Rules Concepts](docs/concept-taint-rules.md) -- the hand-maintained taint rules document set and its contracts
- [Taint Rules Design](docs/design-taint-rules.md) -- rules resource layout, validation and maintenance rules
- [Value Rules Concepts](docs/concept-value-rules.md) -- the hand-maintained value rules set, review reasons, corpus gaps
- [Value Rules Design](docs/design-value-rules.md) -- value rules resource layout, validation and maintenance rules
- [Implementation Notes](docs/impl.md) -- commons-phpmodels API findings, developer instructions
- [Performance](docs/performance.md) -- lookup benchmark procedure and baselines

## For Agents

Agent-consumable documentation index at `docs/llms.txt` ([llmstxt.org](https://llmstxt.org) format).

## Citation

```bibtex
@inproceedings{xu2026cobra,
  title     = {CoBrA: Context-, Branch-sensitive Static Analysis for Detecting Taint-style Vulnerabilities in PHP Web Applications},
  author    = {Xu, Yichao and Kang, Mingqing and Thimmaiah, Neil and Gjomemo, Rigel and Venkatakrishnan, V. N. and Cao, Yinzhi},
  booktitle = {Proceedings of the 48th IEEE/ACM International Conference on Software Engineering (ICSE)},
  year      = {2026},
  address   = {Rio de Janeiro, Brazil}
}
```

## License

GPL-2.0-only
