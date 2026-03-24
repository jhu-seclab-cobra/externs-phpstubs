# PHP Stubs Library Concept Document

## 1. Context

**Problem Statement**
PHP static analysis engines must distinguish built-in functions, classes, methods, and constants from user-defined code at every call site, class reference, and constant access. A naive approach couples this lookup to a disk-backed database with per-query I/O and deserialization overhead, creating a performance bottleneck on the hot path. This library provides an independent, high-performance registry of PHP built-in entity metadata with zero external runtime dependencies.

**System Role**
This library provides a read-only registry of PHP built-in entity metadata, consumable by any PHP static analysis tool or interpreter.

**Data Flow**
- **Inputs:** Pre-compiled binary index (`builtin.bin`) derived from JetBrains PhpStorm stubs
- **Outputs:** Existence checks (boolean), stub records (name + extension), raw serialized bytes (for IValue reconstruction)
- **Connections:** `builtin.bin` (bundled resource) → PhpStubs registry → Consumer modules

**Scope Boundaries**
- **Owned:** Binary index loading, two-tier caching, existence checks, record retrieval, keyword/scalar type classification, raw data access for IValue reconstruction
- **Not Owned:** PhpStorm stubs source files, IValue deserialization (consumer responsibility via `commons-value`), interpreter dispatch logic, built-in function semantic modeling

## 2. Concepts

**Conceptual Diagram**
```
                                    [externs-phpstubs library]
                                   +---------------------------------+
  builtin.bin (978 KB)             |          PhpStubs               |
  (bundled resource,          ---> |   (singleton registry)          |
   from PhpStorm stubs)            |                                 |
                                   |  Tier 1: Set<String> per section|
                                    |    (immutable, ~1 MB)           |
                                    |    -> containsFunc/Class/...    |
                                    |                                 |
                                    |  Tier 2: Map<String, ByteArray> |
                                    |    (immutable, compact)         |
                                    |    -> searchFunc/Class/...      |
                                    |    -> ConcurrentHashMap cache   |
                                    +---------------------------------+
                                           |
                                           v
                                    [Consumer modules]
                                    (any PHP analysis tool)
```

**Core Concepts**

- **Two-Tier Loading.**
  The registry separates existence checking from full record retrieval. Tier 1 holds only normalized key strings in immutable `Set<String>` collections — these support O(1) `contains()` calls with zero object allocation and zero synchronization. Tier 2 holds the raw serialized bytes (`Map<String, ByteArray>`) from the original IValue data. Full `StubRecord` objects are constructed lazily on first value access and cached in a `ConcurrentHashMap`. This design ensures the hot path (existence check) never triggers deserialization.

- **Immutable-After-Init Thread Safety.**
  All base data structures (`Set`, `Map`, `StubData`, `StubSection`) are fully immutable after the one-time lazy initialization. The `lazy` delegate uses `LazyThreadSafetyMode.SYNCHRONIZED` for safe concurrent first-access. After initialization, all reads are lock-free. The per-entry deserialization cache uses `ConcurrentHashMap.computeIfAbsent`, which is lock-free for keys that already exist in the cache.

- **Four Stub Sections.**
  PHP built-in entities are organized into four sections: functions (~5,000 entries), classes (~1,500 entries), methods (~9,800 entries), and constants (~6,000 entries). Each section is an independent `StubSection` instance with its own key set, raw data map, and deserialization cache. The section boundaries match the original PhpStorm stubs organization.

- **Keyword and Scalar Hardcoding.**
  PHP language keywords that behave as functions (`echo`, `isset`, `require`, etc.) and scalar type names (`int`, `string`, `array`, etc.) are hardcoded sets within the registry. These do not appear in the binary index. Keyword lookups return synthetic `StubRecord` instances with extension `"keyword"`; scalar type lookups return records with extension `"Scalar"`.

- **Name Normalization.**
  All input names are normalized before lookup: converted to lowercase and stripped of leading `/` prefix. This ensures case-insensitive matching and handles both qualified (`/strlen`) and unqualified (`strlen`) PHP names transparently.

- **Custom Binary Format.**
  The `builtin.bin` file uses a compact binary format: a 5-byte header (magic `0x43534253` + version byte), followed by four sections. Each section contains an entry count, then entries of `[UTF key][int value-length][bytes value-data]`. The value bytes are the original `DftByteArraySerializerImpl` output from `commons-value`, preserved verbatim for lossless reconstruction.

- **Raw Data Access.**
  For consumers that need the original `IValue` objects (e.g., `PhpLibraryUtils` returning `ListVal`/`MapVal`), the registry exposes raw byte arrays via `getFuncRawData()` etc. The consumer deserializes these with their own `DftByteArraySerializerImpl` instance. This keeps `commons-value` out of the library's dependency graph.

## 3. Contracts & Flow

**Data Contracts**
- **With consumers (hot path):** Consumers call `PhpStubs.containsFunc(name)` / `containsClass(name)` etc. for O(1) existence checks. No deserialization, no allocation.
- **With consumers (cold path):** Consumers call `PhpStubs.searchFunc(name)` for `StubRecord` retrieval, or `PhpStubs.getFuncRawData(name)` for raw bytes. Raw bytes can be deserialized to domain objects by the consumer using their own serializer (e.g., `DftByteArraySerializerImpl`).

**Internal Processing Flow**
1. **Lazy initialization** — On first access to any `PhpStubs` method, the `lazy` delegate triggers `loadDefault()`
2. **Binary loading** — `loadFromStream()` reads the `builtin.bin` resource via `DataInputStream`, validates magic and version
3. **Section parsing** — For each of four sections: reads entry count, then reads key-value pairs into `Set<String>` (keys) and `Map<String, ByteArray>` (raw data)
4. **Immutable freeze** — Parsed collections are wrapped as immutable (`toSet()`, `toMap()`) and stored in a `StubData` instance
5. **Hot-path query** — `containsFunc("strlen")` calls `Set.contains()` on the functions section's key set
6. **Cold-path query** — `searchFunc("strlen")` calls `StubSection.get()`, which uses `ConcurrentHashMap.computeIfAbsent()` to lazily extract the extension name from the raw bytes and cache the resulting `StubRecord`
7. **Raw access** — `getFuncRawData("strlen")` returns the raw `ByteArray` directly from the immutable map

## 4. Scenarios

- **Typical (hot path):** A consumer encounters a function call `strlen($x)` and calls `PhpStubs.containsFunc("strlen")`, which normalizes to `"strlen"`, checks the immutable `Set<String>`, and returns `true` in O(1). No deserialization, no allocation, no locking.

- **Typical (cold path):** A consumer needs the extension name for `"strlen"`. It calls `PhpStubs.searchFunc("strlen")`, which triggers `StubSection.get("strlen")`. On first access, `ConcurrentHashMap.computeIfAbsent` parses the ListVal header from the raw bytes to extract `"standard"`, constructs `StubRecord(name="strlen", extension="standard")`, and caches it. Subsequent calls return the cached instance.

- **Boundary (keyword function):** `PhpStubs.containsFunc("echo")` returns `true` via the hardcoded `KEYWORD_FUNC_NAMES` set. `PhpStubs.searchFunc("echo")` returns a synthetic `StubRecord(name="echo", extension="keyword")` without touching the binary index.

- **Boundary (unknown name):** `PhpStubs.containsFunc("my_custom_func")` normalizes and checks the key set — returns `false`. No fallback, no exception. `PhpStubs.searchFunc("my_custom_func")` returns `null`.

- **Interaction (IValue reconstruction):** A consumer needs the original `ListVal` for `"strlen"`. It calls `PhpStubs.getFuncRawData("strlen")` to get the raw bytes, then deserializes them with its own serializer (e.g., `DftByteArraySerializerImpl.deserialize()`). This keeps `commons-value` as a consumer dependency only, not a library dependency.

- **Interaction (concurrent access):** Multiple threads call `PhpStubs.containsFunc()` simultaneously. All reads hit the immutable `Set<String>` — no contention, no synchronization. If two threads call `searchFunc("strlen")` for the first time simultaneously, `ConcurrentHashMap.computeIfAbsent` ensures exactly one computes the `StubRecord`; the other receives the cached result.
