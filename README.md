# externs-phpstubs

[![codecov](https://codecov.io/gh/jhu-seclab-cobra/externs-phpstubs/branch/main/graph/badge.svg)](https://codecov.io/gh/jhu-seclab-cobra/externs-phpstubs)
![Kotlin JVM](https://img.shields.io/badge/Kotlin%20JVM-2.4.20%20%7C%20JVM%2021%2B-blue?logo=kotlin)
[![Release](https://img.shields.io/badge/release-v0.13.0-blue.svg)](https://github.com/jhu-seclab-cobra/externs-phpstubs/releases/tag/v0.13.0)
[![last commit](https://img.shields.io/github/last-commit/jhu-seclab-cobra/externs-phpstubs)](https://github.com/jhu-seclab-cobra/externs-phpstubs/commits/main)
[![JitPack](https://jitpack.io/v/jhu-seclab-cobra/externs-phpstubs.svg)](https://jitpack.io/#jhu-seclab-cobra/externs-phpstubs)
![Repo Size](https://img.shields.io/github/repo-size/jhu-seclab-cobra/externs-phpstubs)
[![license](https://img.shields.io/github/license/jhu-seclab-cobra/externs-phpstubs)](./LICENSE)

> The name identifies external PHP declaration stubs.

Looks up PHP declarations and their value and taint Facts by PHP name.

## Install

Requires JDK 21 or later and a Gradle Kotlin/JVM project.

```kotlin
repositories { maven { url = uri("https://jitpack.io") } }
dependencies { implementation("com.github.jhu-seclab-cobra:externs-phpstubs:0.13.0") }
```

## Usage

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs

val record = PhpStubs.function("strlen")
println(record?.extension)
```

## API

[Stubs API](docs/llms/stubs.md) lists `BuiltinLookup`, `PhpStubs`, `BuiltinRecord`, Fact types, exact and pattern queries, consumer sets, Library Set selection and errors, with signatures and return types.

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

Please cite the associated paper when using this library.

## Documentation

- [Concepts](docs/concept.md): responsibilities, inputs and outputs.
- [Design](docs/design.md): resource ownership, mounting and errors.
- [Library Set selection](docs/design-taint-libraries.md): available package metadata and selection API.

## For Agents

Agent-consumable documentation index at [docs/llms.txt](docs/llms.txt) (llmstxt.org format).

## License

GPL-2.0-only
