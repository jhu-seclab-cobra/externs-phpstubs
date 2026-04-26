# COBRA.EXTERNS.PHPSTUBS

> Named for the PHP stub definitions it indexes — built-in function, class, method, and constant metadata with dataflow summaries.

Read-only Kotlin registry for PHP built-in stubs with typed metadata, dataflow rules, and constant values. Loaded from YAML files at startup.

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
substr?.flowsToReturn                        // setOf(0) — param 0 data flows to return

// Class hierarchy
val cls = PhpStubs.searchClass("runtimeexception")
cls?.parent                                  // "exception"

// Constant values
PhpStubs.searchGlobalConst("PHP_INT_MAX")?.value  // "9223372036854775807"
```

## API

**`PhpStubs`** — singleton registry.

| Method | Return |
|--------|--------|
| `containsFunc/Class/Method/Const(name)` | `Boolean` |
| `searchFunc(name)` | `StubRecord.Function?` |
| `searchClass(name)` | `StubRecord.PhpClass?` |
| `searchMethod(name, className?)` | `Pair<String, StubRecord.Method>?` |
| `searchGlobalConst(name)` | `StubRecord.Constant?` |
| `searchClassConst(name, className?)` | `StubRecord.ClassConstant?` |
| `getAllFuncNames/ClassNames/MethodNames/ConstNames()` | `Set<String>` |

**`StubRecord`** — sealed class with subtypes: `Function`, `Method`, `PhpClass`, `Constant`, `ClassConstant`, `Property`. Each subtype carries only the fields relevant to its entity kind.

## Data Sources

Stub data derived from the following open-source projects:

| Source | Data | License |
|--------|------|---------|
| [JetBrains/phpstorm-stubs](https://github.com/JetBrains/phpstorm-stubs) | Function signatures, class definitions, constant values | [Apache-2.0](https://github.com/JetBrains/phpstorm-stubs/blob/master/LICENSE) |
| [vimeo/psalm](https://github.com/vimeo/psalm) | Dataflow annotations (`@psalm-flow`), function call map | [MIT](https://github.com/vimeo/psalm/blob/master/LICENSE) |

## Documentation

- [Concepts & Terminology](docs/idea.md) — tag-based YAML format, dataflow summaries, eager loading
- [Design](docs/design.md) — sealed class hierarchy, YAML schema, type specifications, validation rules
- [Implementation Notes](docs/impl.md) — developer instructions, library gotchas

## For Agents

Agent-consumable documentation index at `docs/llms.txt` ([llmstxt.org](https://llmstxt.org) format).

## Citation

If you use this repository in your research, please cite our paper:

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
