# COBRA.EXTERNS.PHPSTUBS

[![](https://jitpack.io/v/jhu-seclab-cobra/externs-phpstubs.svg)](https://jitpack.io/#jhu-seclab-cobra/externs-phpstubs)
[![license](https://img.shields.io/github/license/jhu-seclab-cobra/externs-phpstubs)](./LICENSE)

A Kotlin library that provides a read-only registry for PHP built-in function, class, method, and constant stubs. Backed by a compact binary index (~1 MB), it supports O(1) existence checks and lazy record retrieval.

## Coverage

| Category  | Count  | Examples                                    |
|-----------|--------|---------------------------------------------|
| Functions | ~5,000 | `strlen`, `array_map`, `echo`, `isset`      |
| Classes   | ~1,500 | `Exception`, `PDO`, `int`, `bool`           |
| Methods   | ~9,800 | `PDO::query`, `SplStack::push`              |
| Constants | ~6,000 | `PHP_EOL`, `SORT_ASC`, `PDO::FETCH_ASSOC`   |

Includes 14 keyword functions (`echo`, `isset`, `require`, `include`, etc.) and 5 scalar types (`int`, `float`, `string`, `bool`, `array`) as synthetic entries.

**Not covered**: user-defined functions/classes, PECL-only extensions not bundled with PHP, runtime-generated constants.

## Requirements

- Java 21+

## Installation

Add JitPack repository and the dependency to `build.gradle.kts`:

```kotlin
repositories {
    maven { url = uri("https://jitpack.io") }
}

dependencies {
    implementation("com.github.jhu-seclab-cobra:externs-phpstubs:0.1.0")
}
```

## Usage

### Kotlin

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs

// Existence checks — O(1), zero allocation
PhpStubs.containsFunc("strlen")                   // true
PhpStubs.containsClass("Exception")               // true
PhpStubs.containsMethod("query", "mysqli")         // true
PhpStubs.containsConst("PHP_EOL")                  // true

// Record retrieval — lazy deserialization, cached after first access
val func = PhpStubs.searchFunc("strlen")
println("${func?.name} from ${func?.extension}")   // strlen from standard

val method = PhpStubs.searchMethod("query", "mysqli")
println(method?.first)                              // mysqli::query

// Bulk access
val allFunctions = PhpStubs.getAllFuncNames()       // Set<String>
val allClasses   = PhpStubs.getAllClassNames()
val allMethods   = PhpStubs.getAllMethodNames()
val allConstants  = PhpStubs.getAllConstNames()
```

### Java

```java
import edu.jhu.cobra.externs.phpstubs.PhpStubs;
import edu.jhu.cobra.externs.phpstubs.StubRecord;

boolean hasFunc = PhpStubs.INSTANCE.containsFunc("strlen");

StubRecord func = PhpStubs.INSTANCE.searchFunc("strlen");
System.out.println(func.getName() + " from " + func.getExtension());
```

### Name Normalization

All lookups automatically lowercase the input and strip a leading `/`. These are equivalent:

```kotlin
PhpStubs.containsFunc("Strlen")
PhpStubs.containsFunc("/strlen")
PhpStubs.containsFunc("STRLEN")
```

## License

[GNU 2.0](./LICENSE)
