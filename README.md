# COBRA.EXTERNS.PHPSTUBS

> Named for the PHP stub definitions it indexes — built-in function, class, method, and constant metadata.

Read-only Kotlin registry for PHP built-in stubs, backed by a compact binary index (~1 MB) with O(1) existence checks and lazy record retrieval.

[![](https://jitpack.io/v/jhu-seclab-cobra/externs-phpstubs.svg)](https://jitpack.io/#jhu-seclab-cobra/externs-phpstubs)
[![license](https://img.shields.io/github/license/jhu-seclab-cobra/externs-phpstubs)](./LICENSE)

## Install

Requires Java 21+. Add JitPack repository and the dependency to `build.gradle.kts`:

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

// Existence checks — O(1)
PhpStubs.containsFunc("strlen")         // true
PhpStubs.containsClass("Exception")     // true
PhpStubs.containsMethod("query", "mysqli") // true
PhpStubs.containsConst("PHP_EOL")       // true

// Record retrieval — lazy, cached after first access
val func = PhpStubs.searchFunc("strlen")
println("${func?.name} from ${func?.extension}") // strlen from standard
```

All lookups normalize input: lowercase and strip leading `/`. `"Strlen"`, `"/strlen"`, `"STRLEN"` are equivalent.

## API

**`PhpStubs`** (singleton) — query entry point for all sections.

| Method | Return | Description |
|--------|--------|-------------|
| `containsFunc/Class/Method/Const(name)` | `Boolean` | O(1) existence check |
| `searchFunc/Class(name)` | `StubRecord?` | Lazy record retrieval |
| `searchMethod(name, className?)` | `Pair<String, StubRecord>?` | Method lookup, suffix scan if no class |
| `searchGlobalConst/ClassConst(name, className?)` | `StubRecord?` | Constant lookup |
| `getAllFuncNames/ClassNames/MethodNames/ConstNames()` | `Set<String>` | All keys in section |
| `getKeywordFuncNames()` | `Set<String>` | Hardcoded keyword functions |
| `getScalarTypeNames()` | `Set<String>` | Hardcoded scalar types |

**`StubRecord(name: String, extension: String)`** — stub metadata.

**Exceptions**: `StubIndexNotFoundException`, `StubIndexInvalidException`.

## Documentation

- [Concepts & Terminology](docs/idea.md) — problem context, two-tier architecture, core concepts, scenarios
- [Design](docs/design.md) — class/type specifications, function signatures, exceptions, validation rules
- [Implementation Notes](docs/impl.md) — external dependencies and developer instructions

## For Agents

Agent-consumable documentation index at `docs/llms.txt` (llmstxt.org format).

## License

GPL-2.0-only
