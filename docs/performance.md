# externs-phpstubs Performance

## Current Baseline

Measured on: 2026-03-24 | JVM: JDK 21 | JVM flags: `-Xmx2g -Xms1g`
Benchmark: `./gradlew performanceTest` | Warmup: 5 runs | Measurement: 7 runs (median)
Dataset: 22,477 total keys (5,021 functions + 1,538 classes + 9,872 methods + 6,046 constants)

### Hot Path — Existence Checks (100K ops/run)

| Operation | Median (ms) | ns/op | Throughput (ops/s) |
|-----------|------------|-------|-------------------|
| containsFunc — known | 1.91 | 19.1 | 52,478,507 |
| containsFunc — unknown | 1.92 | 19.2 | 52,155,780 |
| containsFunc — keywords | 3.50 | 35.0 | 28,537,118 |
| containsFunc — uppercase | 2.55 | 25.5 | 39,208,644 |
| containsFunc — slash prefix | 3.01 | 30.1 | 33,255,283 |
| containsClass — known | 1.87 | 18.7 | 53,505,750 |
| containsClass — scalar types | 1.31 | 13.1 | 76,122,792 |
| containsMethod — with class | 4.95 | 49.5 | 20,203,040 |
| containsMethod — suffix only | 2.00 | 20.0 | 50,004,175 |
| containsConst | 1.67 | 16.7 | 59,989,513 |

### Cold Path — Record Retrieval (100K ops/run)

| Operation | Median (ms) | ns/op | Throughput (ops/s) |
|-----------|------------|-------|-------------------|
| searchFunc — known | 2.36 | 23.6 | 42,419,308 |
| searchFunc — keywords | 1.65 | 16.5 | 60,543,352 |
| searchClass — scalar types | 1.59 | 15.9 | 62,937,613 |
| searchMethod — with class | 6.18 | 61.8 | 16,188,760 |
| searchMethod — suffix only | 3.89 | 38.9 | 25,711,071 |

### Memory

| Metric | Value |
|--------|-------|
| Heap after full load | 15.77 MB |
| Total keys | 22,477 |

## Key Improvements

| ID | Title | Target | Impact | Status |
|----|-------|--------|--------|--------|
| P1-1 | Fast-path `normalize()` | Hot-path allocation | Avoid 2 String allocs per query when input is already lowercase ASCII | KEEP |
| P1-2 | Reverse suffix index | O(n) → O(1) suffix lookup | HashMap lookup replaces linear scan over ~10K method/constant keys | KEEP |
| P1-3 | Cache synthetic records | Cold-path allocation | Zero allocation for keyword/scalar lookups (fixed set of 22 records) | KEEP |
| P1-4 | Unmodifiable wrappers | Load-time memory | Avoid duplicating ~22K entries via `toSet()`/`toMap()` at init | KEEP |

## Completed Optimizations

### P1-1: Fast-path `normalize()` to avoid hot-path allocations
- **File**: `PhpStubs.kt`
- **Change**: Check for leading `/` before `substring`; skip `lowercase()` when input is already all-lowercase ASCII.
- **Impact**: Eliminates 1-2 String allocations per query call on the common case (lowercase input without `/` prefix).

### P1-2: Reverse suffix index for O(1) method/constant lookup
- **File**: `StubSection.kt`, `PhpStubs.kt`
- **Change**: Added lazily-built `suffixIndex` map in `StubSection` (suffix after `::` → full keys). Replaced `keys.any { it.endsWith(suffix) }` and `keys.firstOrNull { it.endsWith(suffix) }` with `HashMap.containsKey`/`HashMap.get`.
- **Impact**: `containsMethod(name, null)`, `searchMethod(name, null)`, `searchClassConst(name, null)` go from O(n) to O(1).
- **Measured**: containsMethod suffix-only at 20.0 ns/op (50M ops/s) — comparable to direct key lookups, confirming O(1) behavior.

### P1-3: Cache synthetic keyword/scalar StubRecord instances
- **File**: `PhpStubs.kt`
- **Change**: Pre-built `KEYWORD_RECORDS` and `SYNTHETIC_CLASS_RECORDS` maps. `searchFunc`/`searchClass` return cached instances.
- **Impact**: Zero allocation on repeated lookups for 15 keywords + 5 scalar types + 2 special types.
- **Measured**: searchFunc-keyword at 16.5 ns/op (60M ops/s), searchClass-scalar at 15.9 ns/op (63M ops/s) — fastest retrieval paths due to cached records.

### P1-4: Unmodifiable wrappers instead of defensive copies
- **File**: `PhpStubs.kt`
- **Change**: `readSection()` wraps `LinkedHashSet`/`HashMap` with `Collections.unmodifiableSet/Map` instead of `toSet()`/`toMap()` which copy all entries.
- **Impact**: Reduces init-time memory spike and avoids ~22K entry duplication per section (4 sections).

## Evaluated & Rejected

| ID | Title | Reason |
|----|-------|--------|
| P1-5 | StringBuilder for method key concat | SKIP — Kotlin compiler already optimizes string templates to StringBuilder. No measurable benefit. |

## Candidates

(empty — round 1 complete)

## Remaining Known Bottlenecks

- `containsMethod — with class` (49.5 ns/op) is 2.5x slower than simple `containsFunc` (19.1 ns/op) due to double `normalize()` + string concatenation for the composite key.
- `searchMethod — with class` (61.8 ns/op) is the slowest operation — combines double normalize + concat + ConcurrentHashMap lookup.
- Deserialization via `DftByteArraySerializerImpl.deserialize()` is the dominant cost on cold-path lookups. Optimization depends on commons-value internals.
- `getAll()` forces eager deserialization of entire sections.

## Key Insights

1. This is a read-only lookup library — all data is immutable after load. Optimization focus is on allocation reduction and algorithmic complexity for lookups.
2. Two-tier architecture already avoids deserialization on hot path; main gains come from reducing String allocations in normalize/lookup.
3. Kotlin string templates (`"$a::$b"`) compile to `StringBuilder` — manual StringBuilder offers no benefit.
4. `Collections.unmodifiableSet/Map` is cheaper than `toSet()`/`toMap()` for preventing mutation of internal collections, as it wraps without copying.
5. The `normalize()` fast-path is effective: lowercase ASCII input (19.1 ns/op) vs uppercase (25.5 ns/op) vs slash-prefix (30.1 ns/op) — the common case (already lowercase, no prefix) is the fastest.
6. Cached synthetic records (P1-3) make keyword/scalar retrieval (16 ns/op) faster than index-based retrieval (24 ns/op) by skipping ConcurrentHashMap lookup entirely.
7. Suffix-only method lookup (20 ns/op) is now faster than with-class lookup (49.5 ns/op) thanks to the reverse index (P1-2) — the reverse index avoids double normalize + concat.

## Benchmark Infrastructure

- Test class: `PhpStubsPerformanceTest` (tagged `@Tag("performance")`)
- Run: `./gradlew performanceTest`
- Excluded from normal `./gradlew test` via `excludeTags("performance")`
- Operations per run: 100,000
- Warmup: 5 runs, Measurement: 7 runs (median reported)
- JVM flags: `-Xmx2g -Xms1g`
