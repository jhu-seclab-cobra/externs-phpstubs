# COBRA.EXTERNS.PHPSTUBS

> PHP built-in declaration registry for static analysis.

Lookup of PHP built-in functions, classes, methods, and constants as commons-phpmodels entries with extension provenance.

[![codecov](https://codecov.io/gh/jhu-seclab-cobra/externs-phpstubs/branch/main/graph/badge.svg)](https://codecov.io/gh/jhu-seclab-cobra/externs-phpstubs)
![Kotlin JVM](https://img.shields.io/badge/Kotlin%20JVM-2.0.1%20%7C%20JVM%201.8%2B-blue?logo=kotlin)
[![Release](https://img.shields.io/badge/release-v0.2.0-blue.svg)](https://github.com/jhu-seclab-cobra/externs-phpstubs/releases/tag/v0.2.0)
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
    implementation("com.github.jhu-seclab-cobra:externs-phpstubs:0.2.0")
}
```

## Usage

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs
import edu.jhu.cobra.externs.phpstubs.callableSignature
import edu.jhu.cobra.externs.phpstubs.typedSignature

// Existence checks
PhpStubs.containsFunction("strlen")             // true
PhpStubs.containsClass("Exception")         // true

// Function entry: extension provenance plus the decoded model
val strlen = PhpStubs.findFunction("strlen")
strlen?.extension                            // "standard"
strlen?.callableSignature?.returnType        // DeclaredType("int")
strlen?.callableSignature?.params            // [ParameterInfo("string", ...)]

// Declared flows come from the model body
val substr = PhpStubs.findFunction("substr")
substr?.model?.body?.propagation             // [Propagation(argument(0) -> return)]

// Constants (case-sensitive by default, matching PHP semantics)
PhpStubs.findConstant("PHP_INT_MAX")?.typedSignature?.value    // "9223372036854775807"
PhpStubs.findConstant("php_int_max")                           // null (case mismatch)
PhpStubs.findConstant("php_int_max", caseSensitive = false)    // folded lookup
```

## API

**`PhpStubs`** -- singleton facade. Names go through the [commons-phpmodels](https://github.com/jhu-seclab-cobra/commons-phpmodels) subject creators: functions, classes, and methods fold case, a leading `\` is stripped, and constants keep their case. A name that is not a PHP identifier spelling raises `IllegalArgumentException`.

| Method | Return |
|--------|--------|
| `containsFunction(name)` | `Boolean` |
| `containsClass(name)` | `Boolean` |
| `containsMethod(name, owner?)` | `Boolean` |
| `containsConstant(name, caseSensitive?)` | `Boolean` |
| `findFunction(name)` | `StubEntry<FunctionSubject>?` |
| `findClass(name)` | `StubEntry<ClassSubject>?` |
| `findMethod(name, owner?)` | `StubEntry<MethodSubject>?` |
| `findConstant(name, caseSensitive?)` | `StubEntry<ConstantSubject>?` |
| `findClassConstant(name, owner?, caseSensitive?)` | `StubEntry<ClassConstantSubject>?` |
| `functionNames` | `Set<String>` |
| `classNames` | `Set<String>` |
| `methodNames` | `Set<String>` |
| `constantNames` | `Set<String>` |
| `keywordFunctionNames` | `Set<String>` |
| `scalarTypeNames` | `Set<String>` |

**`StubEntry<S>`** -- data class `(subject: S, model: SubjectModel, extension: String)`. Typed accessors: `callableSignature` (function, method), `classSignature` (class), `typedSignature` (constant, class constant), `propertySignature` (property).

**`StubRegistry`** -- the frozen per-kind maps behind the facade, built by `StubLoader.loadAll()`.

## Background

Model documents derived from [JetBrains/phpstorm-stubs](https://github.com/JetBrains/phpstorm-stubs) (signatures, Apache-2.0) and [vimeo/psalm](https://github.com/vimeo/psalm) (dataflow annotations, MIT), emitted in the [commons-phpmodels](https://github.com/jhu-seclab-cobra/commons-phpmodels) format. Language constructs (`echo`, `isset`, `int`, ...) are declared as data under `models/language/`.

## Documentation

- [Concepts](docs/concept.md) -- generated layer over commons-phpmodels, extension provenance, lookup semantics
- [Design](docs/design.md) -- entry, registry, loader, and facade specifications; corpus rules
- [Implementation Notes](docs/impl.md) -- commons-phpmodels API findings, developer instructions

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
