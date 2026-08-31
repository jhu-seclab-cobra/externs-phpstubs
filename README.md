# COBRA.EXTERNS.PHPSTUBS

> PHP built-in entity registry for static analysis.

Typed lookup of PHP standard library functions, classes, methods, constants, and their metadata — signatures, return types, parameter info, dataflow summaries, and constant values.

[![codecov](https://codecov.io/gh/jhu-seclab-cobra/externs-phpstubs/branch/main/graph/badge.svg)](https://codecov.io/gh/jhu-seclab-cobra/externs-phpstubs)
![Kotlin JVM](https://img.shields.io/badge/Kotlin%20JVM-2.0.1%20%7C%20JVM%201.8%2B-blue?logo=kotlin)
[![Release](https://img.shields.io/badge/release-v0.1.0-blue.svg)](https://github.com/jhu-seclab-cobra/externs-phpstubs/releases/tag/v0.1.0)
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
    implementation("com.github.jhu-seclab-cobra:externs-phpstubs:0.1.0")
}
```

## Usage

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs

// Existence checks
PhpStubs.containsFunc("strlen")             // true
PhpStubs.containsClass("Exception")         // true

// Function metadata
val func = PhpStubs.searchFunc("strlen")
func?.returnType                             // PhpType.INT
func?.params                                 // [StubParam("string", STRING)]

// Dataflow summary
val substr = PhpStubs.searchFunc("substr")
substr?.flowsToReturn                        // setOf(0) -- param 0 flows to return

// Class hierarchy
val cls = PhpStubs.searchClass("runtimeexception")
cls?.parent                                  // "exception"

// Constants (case-sensitive by default, matching PHP semantics)
PhpStubs.searchGlobalConst("PHP_INT_MAX")?.value    // "9223372036854775807"
PhpStubs.searchGlobalConst("php_int_max")           // null (case mismatch)
PhpStubs.searchGlobalConst("php_int_max", caseSensitive = false)?.value  // "9223372036854775807"
```

## API

**`PhpStubs`** -- singleton facade. All lookups are case-insensitive for functions, classes, and methods. Constants are case-sensitive by default.

| Method | Return |
|--------|--------|
| `containsFunc(name)` | `Boolean` |
| `containsClass(name)` | `Boolean` |
| `containsMethod(methodName, className?)` | `Boolean` |
| `containsConst(name, caseSensitive?)` | `Boolean` |
| `searchFunc(name)` | `StubRecord.Function?` |
| `searchClass(name)` | `StubRecord.PhpClass?` |
| `searchMethod(methodName, className?)` | `Pair<String, StubRecord.Method>?` |
| `searchGlobalConst(name, caseSensitive?)` | `StubRecord.Constant?` |
| `searchClassConst(constName, className?, caseSensitive?)` | `StubRecord.ClassConstant?` |
| `getAllFuncNames()` | `Set<String>` |
| `getAllClassNames()` | `Set<String>` |
| `getAllMethodNames()` | `Set<String>` |
| `getAllConstNames()` | `Set<String>` |

**`StubRecord`** -- sealed class. Subtypes: `Function`, `Method`, `PhpClass`, `Constant`, `ClassConstant`, `Property`.

## Background

Stub data derived from [JetBrains/phpstorm-stubs](https://github.com/JetBrains/phpstorm-stubs) (signatures, Apache-2.0) and [vimeo/psalm](https://github.com/vimeo/psalm) (dataflow annotations, MIT).

## Documentation

- [Concepts](docs/concept.md) -- tag-based YAML format, dataflow summaries, eager loading
- [Design](docs/design.md) -- sealed class hierarchy, YAML schema, type specifications
- [Implementation Notes](docs/impl.md) -- developer instructions, library gotchas

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
