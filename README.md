# COBRA.EXTERNS.PHPSTUBS

![Kotlin JVM](https://img.shields.io/badge/Kotlin%20JVM-2.2.21%20%7C%20JVM%2021%2B-blue?logo=kotlin)
[![Release](https://img.shields.io/badge/release-v0.1.0-blue.svg)](https://github.com/jhu-seclab-cobra/externs-phpstubs/releases/tag/v0.1.0)
[![last commit](https://img.shields.io/github/last-commit/jhu-seclab-cobra/externs-phpstubs)](https://github.com/jhu-seclab-cobra/externs-phpstubs/commits/main)
[![](https://jitpack.io/v/jhu-seclab-cobra/externs-phpstubs.svg)](https://jitpack.io/#jhu-seclab-cobra/externs-phpstubs)
![Repo Size](https://img.shields.io/github/repo-size/jhu-seclab-cobra/externs-phpstubs)
[![license](https://img.shields.io/github/license/jhu-seclab-cobra/externs-phpstubs)](./LICENSE)

A Kotlin library that provides a high-performance, thread-safe registry for PHP built-in function, class, method, and constant stubs. It uses a two-tier loading strategy with a compact binary format for optimal lookup performance — O(1) existence checks with zero allocation, and lazy deserialization for full record retrieval.

## Features

- Two-tier loading: eager key sets for O(1) existence checks, lazy deserialization for full records
- Thread-safe by design: immutable data structures with lock-free concurrent caching
- Self-contained binary stub index (~1 MB for ~22K entries) — no external dependencies
- Built-in support for PHP keyword functions (`echo`, `isset`, `require`, etc.) and scalar types
- Case-insensitive lookups with automatic name normalization

## Requirements

- Java 21 or higher

## Installation

1. Add JitPack repository to your `build.gradle.kts`:
```kotlin
repositories {
    maven { url = uri("https://jitpack.io") }
}
```

2. Add the dependency:
```kotlin
dependencies {
    implementation("com.github.jhu-seclab-cobra:externs-phpstubs:0.1.0")
}
```

## Usage

### Kotlin

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs

// Existence checks (Tier 1 — fast path, zero allocation)
PhpStubs.containsFunc("strlen")          // true
PhpStubs.containsFunc("echo")            // true (keyword)
PhpStubs.containsClass("Exception")      // true
PhpStubs.containsClass("int")            // true (scalar type)
PhpStubs.containsMethod("query", "mysqli") // true
PhpStubs.containsConst("PHP_EOL")        // true

// Full record retrieval (Tier 2 — lazy deserialization)
val func = PhpStubs.searchFunc("strlen")
println("${func?.name} from ${func?.extension}")  // strlen from standard

val keyword = PhpStubs.searchFunc("echo")
println(keyword?.extension)  // keyword

val method = PhpStubs.searchMethod("query", "mysqli")
println(method?.first)  // mysqli::query

// Bulk access
val allFunctions = PhpStubs.getAllFuncNames()    // ~5,000 entries
val allClasses = PhpStubs.getAllClassNames()      // ~1,500 entries
val allMethods = PhpStubs.getAllMethodNames()     // ~9,800 entries
val allConstants = PhpStubs.getAllConstNames()    // ~6,000 entries

// Raw data access (for custom deserialization)
val rawBytes = PhpStubs.getFuncRawData("strlen")
```

### Java

```java
import edu.jhu.cobra.externs.phpstubs.PhpStubs;
import edu.jhu.cobra.externs.phpstubs.StubRecord;
import kotlin.Pair;

// Existence checks
boolean hasFunc = PhpStubs.INSTANCE.containsFunc("strlen");
boolean hasClass = PhpStubs.INSTANCE.containsClass("Exception");
boolean hasMethod = PhpStubs.INSTANCE.containsMethod("query", "mysqli");
boolean hasConst = PhpStubs.INSTANCE.containsConst("PHP_EOL");

// Full record retrieval
StubRecord func = PhpStubs.INSTANCE.searchFunc("strlen");
System.out.println(func.getName() + " from " + func.getExtension());

Pair<String, StubRecord> method = PhpStubs.INSTANCE.searchMethod("query", "mysqli");
System.out.println(method.getFirst());  // mysqli::query
```

### Name Normalization

All lookup methods automatically normalize input names:
- Converts to lowercase
- Strips leading `/` prefix

This means `PhpStubs.containsFunc("Strlen")`, `PhpStubs.containsFunc("/strlen")`, and `PhpStubs.containsFunc("STRLEN")` all return `true`.

## Architecture

The library implements a **two-tier loading** strategy:

- **Tier 1 (Hot Path)**: Immutable `Set<String>` of normalized keys, loaded eagerly on first access. Existence checks (`containsFunc`, `containsClass`, etc.) hit only this tier — O(1), zero allocation, zero synchronization.
- **Tier 2 (Cold Path)**: Raw serialized bytes stored in immutable `Map<String, ByteArray>`. Full `StubRecord` objects are deserialized lazily on first value access and cached in a lock-free `ConcurrentHashMap`.

## License

[GNU 2.0](./LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
