# PHP Stubs Library Design Document

## Design Overview

- **Classes**: `PhpStubs`, `StubData`, `StubSection`, `StubRecord`
- **Relationships**: `PhpStubs` contains `StubData`, `StubData` contains four `StubSection` instances, `StubSection` produces `StubRecord`
- **Exceptions**: `StubIndexNotFoundException` extends `RuntimeException`, `StubIndexInvalidException` extends `RuntimeException`, both raised by `PhpStubs`
- **Dependency roles**: Data holders: `StubRecord`, `StubData`. Orchestrator: `PhpStubs`. Helper: `StubSection` (owns cache, provides two-tier lookup).

## Class / Type Specifications

### `PhpStubs` (object)

**Responsibility:** Singleton registry providing all public query APIs for PHP built-in entity lookup.

**State / Fields**

| Field | Type | Description |
|-------|------|-------------|
| `MAGIC` | `Int` | Binary format magic number `0x43534253` ("CSBS"). |
| `VERSION` | `Byte` | Supported binary format version (`1`). |
| `DEFAULT_RESOURCE` | `String` | Classpath resource path `/stubs/builtin.bin`. |
| `KEYWORD_FUNC_NAMES` | `Set<String>` | Hardcoded PHP keyword-functions (`echo`, `isset`, `require`, etc.). |
| `SCALAR_TYPE_NAMES` | `Set<String>` | Hardcoded PHP scalar types (`int`, `float`, `string`, `bool`, `array`). |
| `data` | `StubData` | Lazily loaded, immutable stub data. Uses `LazyThreadSafetyMode.SYNCHRONIZED`. |

**Methods**

| Method | Behavior | Input | Output | Errors |
|--------|----------|-------|--------|--------|
| `loadFromStream(stream)` | Reads and validates a binary input stream, parses four sections into an immutable `StubData`. | `stream: InputStream` — binary stub index. | `StubData` | `StubIndexInvalidException` if magic or version mismatch. |
| `containsFunc(name)` | Tier 1 existence check. Normalizes name, checks functions key set and keyword set. | `name: String` — function name (case-insensitive, optional `/` prefix). | `Boolean` | — |
| `containsClass(name)` | Tier 1 existence check. Normalizes name, checks classes key set, scalar types, `"exit"`, `"resource"`. | `name: String` | `Boolean` | — |
| `containsMethod(methodName, className?)` | Tier 1 existence check. If `className` provided, checks exact `"class::method"` key. Otherwise scans all keys by suffix. | `methodName: String`, `className: String?` | `Boolean` | — |
| `containsConst(name)` | Tier 1 existence check on constants section. | `name: String` | `Boolean` | — |
| `searchFunc(name)` | Tier 2 record retrieval. Returns `StubRecord` from index or synthetic keyword record. | `name: String` | `StubRecord?` — null if not found. | — |
| `searchClass(name)` | Tier 2 record retrieval. Returns `StubRecord` from index or synthetic records for scalars, `"exit"`, `"resource"`. | `name: String` | `StubRecord?` | — |
| `searchMethod(methodName, className?)` | Tier 2 record retrieval. Returns fully-qualified key paired with `StubRecord`. Suffix scan if no className. | `methodName: String`, `className: String?` | `Pair<String, StubRecord>?` | — |
| `searchGlobalConst(name)` | Tier 2 record retrieval for global constants. | `name: String` | `StubRecord?` | — |
| `searchClassConst(constName, className?)` | Tier 2 record retrieval for class constants. Suffix scan if no className. | `constName: String`, `className: String?` | `StubRecord?` | — |
| `getAllFuncNames()` | Returns all function keys from Tier 1. | — | `Set<String>` | — |
| `getAllClassNames()` | Returns all class keys from Tier 1. | — | `Set<String>` | — |
| `getAllMethodNames()` | Returns all method keys from Tier 1. | — | `Set<String>` | — |
| `getAllConstNames()` | Returns all constant keys from Tier 1. | — | `Set<String>` | — |
| `getKeywordFuncNames()` | Returns the hardcoded keyword function name set. | — | `Set<String>` | — |
| `getScalarTypeNames()` | Returns the hardcoded scalar type name set. | — | `Set<String>` | — |
| `getFuncRawData(name)` | Returns raw serialized bytes for consumer-side `IValue` reconstruction. | `name: String` | `ByteArray?` | — |
| `getClassRawData(name)` | Returns raw serialized bytes for a class entry. | `name: String` | `ByteArray?` | — |
| `getMethodRawData(name, className?)` | Returns raw serialized bytes for a method entry. Suffix scan if no className. | `name: String`, `className: String?` | `ByteArray?` | — |
| `getConstRawData(name)` | Returns raw serialized bytes for a constant entry. | `name: String` | `ByteArray?` | — |

---

### `StubData`

**Responsibility:** Immutable container grouping the four stub sections.

**State / Fields**

| Field | Type | Description |
|-------|------|-------------|
| `functions` | `StubSection` | Functions section (~5,000 entries). |
| `classes` | `StubSection` | Classes section (~1,500 entries). |
| `methods` | `StubSection` | Methods section (~9,800 entries). |
| `constants` | `StubSection` | Constants section (~6,000 entries). |

**Companion**

| Field | Type | Description |
|-------|------|-------------|
| `EMPTY` | `StubData` | Singleton with four `StubSection.EMPTY` instances. |

---

### `StubSection`

**Responsibility:** Immutable, thread-safe section implementing two-tier loading — O(1) existence checks (Tier 1) and lazy-deserialized record retrieval with lock-free caching (Tier 2).

**State / Fields**

| Field | Type | Description |
|-------|------|-------------|
| `keys` | `Set<String>` | Immutable set of normalized keys (Tier 1). |
| `rawData` | `Map<String, ByteArray>` | Immutable map of key to serialized value bytes (Tier 2 source). |
| `cache` | `ConcurrentHashMap<String, StubRecord>` | Lazily populated deserialization cache. |

**Methods**

| Method | Behavior | Input | Output | Errors |
|--------|----------|-------|--------|--------|
| `contains(key)` | O(1) set membership check. No allocation, no synchronization. | `key: String` — normalized key. | `Boolean` | — |
| `get(key)` | Returns cached `StubRecord` or deserializes lazily via `computeIfAbsent`. Extracts extension name from raw bytes without full `IValue` deserialization. | `key: String` — normalized key. | `StubRecord?` — null if key absent. | — |
| `getAll()` | Materializes all entries by calling `get()` on every key. | — | `Map<String, StubRecord>` | — |

**Companion Methods**

| Method | Behavior | Input | Output | Errors |
|--------|----------|-------|--------|--------|
| `extractExtension(bytes)` | Parses the first element of a serialized `ListVal` or `StrVal` to extract the extension name. Falls back to `"unknown"` for unrecognized formats. | `bytes: ByteArray` — raw serialized data. | `String` — extension name. | — |

---

### `StubRecord`

**Responsibility:** Immutable data holder representing a single PHP built-in entity.

**State / Fields**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `String` | Normalized entity name (e.g., `"strlen"`, `"pdo::query"`). |
| `extension` | `String` | PHP extension name (e.g., `"standard"`, `"Core"`, `"keyword"`, `"Scalar"`). |

## Function Specifications

### Name Normalization (private)

**`String.normalize()`** — Converts input to lowercase and strips leading `/` prefix. Applied to all lookup inputs before key comparison.

- **Input:** Any PHP entity name string.
- **Output:** Normalized lowercase string without leading `/`.

## Exception / Error Types

| Exception | When Raised |
|-----------|-------------|
| `StubIndexNotFoundException` | Stub index resource cannot be found on the classpath. Takes the resource path as constructor argument. |
| `StubIndexInvalidException` | Binary format validation fails: wrong magic number (`0x43534253` expected) or unsupported version byte. Takes a reason description as constructor argument. |

Both extend `RuntimeException`.

## Validation Rules

### `PhpStubs.loadFromStream`
- Magic number must equal `0x43534253`; otherwise throw `StubIndexInvalidException`.
- Version byte must equal `1`; otherwise throw `StubIndexInvalidException`.
- Stream must contain exactly four sections in order: functions, classes, methods, constants.

### `StubSection.extractExtension`
- If `bytes` is empty, return `"unknown"`.
- If first byte is `0x0C` (LIST type) and total length < 6, return `"unknown"`.
- If computed string length exceeds byte array bounds, return `"unknown"`.
- Recognized type tags: `0x0C` (ListVal), `0x01` (StrVal). All others return `"unknown"`.

### Name Normalization
- All public query methods normalize input before lookup: `lowercase()` then `removePrefix("/")`.
- Callers may pass names in any case and with or without leading `/`.
