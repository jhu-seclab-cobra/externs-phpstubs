# Stubs API

> PHP built-in entity registry with typed metadata and dataflow summaries.

## Quick Start

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs

val func = PhpStubs.searchFunc("strlen")       // StubRecord.Function?
val method = PhpStubs.searchMethod("query", "mysqli")  // Pair<String, StubRecord.Method>?
val cls = PhpStubs.searchClass("Exception")    // StubRecord.PhpClass?
```

## API

### PhpStubs (singleton)

**Existence checks:**

**`containsFunc(name: String): Boolean`** -- Includes keyword functions (`echo`, `isset`, etc.).

**`containsClass(name: String): Boolean`** -- Includes scalar types (`int`, `float`, etc.) and synthetic classes (`exit`, `resource`).

**`containsMethod(methodName: String, className: String? = null): Boolean`** -- Full key lookup when `className` provided; suffix index lookup when null.

**`containsConst(name: String, caseSensitive: Boolean = true): Boolean`** -- Checks both global and class constants. Pass `caseSensitive = false` for case-insensitive lookup.

**Record retrieval:**

**`searchFunc(name: String): StubRecord.Function?`** -- Returns keyword records for `echo`/`isset`/etc., otherwise registry lookup.

**`searchClass(name: String): StubRecord.PhpClass?`** -- Returns registry lookup, falls back to synthetic records for scalar types/`exit`/`resource`.

**`searchMethod(methodName: String, className: String? = null): Pair<String, StubRecord.Method>?`** -- Pair contains the full `"class::method"` key and the record. Suffix index lookup when `className` null.

**`searchGlobalConst(name: String, caseSensitive: Boolean = true): StubRecord.Constant?`** -- Global constants only. Case-sensitive by default.

**`searchClassConst(constName: String, className: String? = null, caseSensitive: Boolean = true): StubRecord.ClassConstant?`** -- Suffix index lookup when `className` null. Constant name case-sensitive by default.

**Bulk key access:**

**`getAllFuncNames(): Set<String>`** -- Registry functions only (excludes keywords).

**`getAllClassNames(): Set<String>`** -- Registry classes only (excludes synthetic).

**`getAllMethodNames(): Set<String>`**

**`getAllConstNames(): Set<String>`** -- Global constants only.

**`getKeywordFuncNames(): Set<String>`** -- echo, empty, eval, exit, die, isset, print, unset, clone, instanceof, shell_exec, include, include_once, require, require_once.

**`getScalarTypeNames(): Set<String>`** -- int, float, string, bool, array.

### StubRecord (sealed class)

Base properties on all 6 subtypes:

**`name: String`** -- Entity name.

**`extension: String`** -- PHP extension (e.g., `"standard"`, `"core"`).

#### StubRecord.Function

**`params: List<StubParam>`**, **`returnType: PhpType`**, **`flowsToReturn: Set<Int>`**

#### StubRecord.Method

**`owningClass: String`**, **`params: List<StubParam>`**, **`returnType: PhpType`**, **`flowsToReturn: Set<Int>`**, **`visibility: Visibility`**, **`isStatic: Boolean`**

#### StubRecord.PhpClass

**`parent: String?`**, **`interfaces: List<String>`**, **`isAbstract: Boolean`**, **`isFinal: Boolean`**

#### StubRecord.Constant

**`type: PhpType`**, **`value: String`**

#### StubRecord.ClassConstant

**`owningClass: String`**, **`type: PhpType`**, **`value: String`**, **`visibility: Visibility`**

#### StubRecord.Property

**`owningClass: String`**, **`type: PhpType`**, **`visibility: Visibility`**, **`isStatic: Boolean`**

### StubParam

**`name: String`**, **`type: PhpType`**, **`optional: Boolean`**, **`defaultValue: String?`**

Invariant: non-optional params cannot have `defaultValue`.

### PhpType

`STRING`, `INT`, `FLOAT`, `BOOL`, `ARRAY`, `OBJECT`, `MIXED`, `VOID`, `NULL`, `CALLABLE`, `RESOURCE`.

Union types in YAML resolve to `MIXED`. Unknown type names raise `StubIndexInvalidException` at load time.

### Visibility

`PUBLIC`, `PROTECTED`, `PRIVATE`.

### Exceptions

**`StubIndexNotFoundException`** -- Classpath resource not found (`index.txt` or YAML file).

**`StubIndexInvalidException`** -- Malformed YAML entry, unknown tag, or missing required field.

## Gotchas

- Function, class, and method lookup inputs are normalized: leading `/` and `\` stripped, then lowercased. Constant lookup inputs only strip the prefix -- constant case is preserved unless `caseSensitive = false`.
- `StubRecord` is a sealed class -- use `searchFunc` for `Function`, `searchClass` for `PhpClass`, `searchMethod` for `Method`, `searchGlobalConst` for `Constant`, `searchClassConst` for `ClassConstant`.
- Keyword functions and scalar type classes are synthetic in-memory records, not loaded from YAML.
- `defaultValue` on `StubParam` is a string representation. Consumer converts to domain types.
- Constants use `.value` field on `StubRecord.Constant` and `StubRecord.ClassConstant`.
- `flowsToReturn` empty = pure computation. Return value does not contain parameter data.
- Taint rules (source/sink/sanitizer) are NOT in this library.
