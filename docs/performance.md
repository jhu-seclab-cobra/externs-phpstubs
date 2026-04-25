# externs-phpstubs Performance

## Current Baseline

**Status: needs re-measurement** -- architecture changed; numbers below are from 2026-03-24 and require revalidation.

Measured on: 2026-03-24 | JVM: JDK 21 | JVM flags: `-Xmx2g -Xms1g`
Benchmark: `./gradlew test -Pperformance` | Warmup: 5 runs | Measurement: 7 runs (median)
Dataset: 22,477 total keys (5,021 functions + 1,538 classes + 9,872 methods + 6,046 constants)

### Hot Path -- Existence Checks (100K ops/run)

| Operation | Median (ms) | ns/op | Throughput (ops/s) |
|-----------|------------|-------|-------------------|
| containsFunc -- known | 1.92 | 19.2 | 51,985,184 |
| containsFunc -- unknown | 1.47 | 14.7 | 67,898,250 |
| containsFunc -- keywords | 1.62 | 16.2 | 61,889,154 |
| containsFunc -- uppercase | 2.56 | 25.6 | 39,025,669 |
| containsFunc -- slash prefix | 2.81 | 28.1 | 35,527,651 |
| containsClass -- known | 1.87 | 18.7 | 53,592,980 |
| containsClass -- scalar types | 1.21 | 12.1 | 82,947,351 |
| containsMethod -- with class | 4.66 | 46.6 | 21,442,354 |
| containsMethod -- suffix only | 1.96 | 19.6 | 51,000,892 |
| containsConst | 1.65 | 16.5 | 60,473,202 |

### Cold Path -- Record Retrieval (100K ops/run)

| Operation | Median (ms) | ns/op | Throughput (ops/s) |
|-----------|------------|-------|-------------------|
| searchFunc -- known | 2.30 | 23.0 | 43,391,797 |
| searchFunc -- keywords | 1.58 | 15.8 | 63,254,427 |
| searchClass -- scalar types | 1.61 | 16.1 | 62,224,501 |
| searchMethod -- with class | 6.13 | 61.3 | 16,321,422 |
| searchMethod -- suffix only | 3.67 | 36.7 | 27,252,597 |

### Memory

| Metric | Value |
|--------|-------|
| Heap after full load | 15.71 MB |
| Total keys | 22,477 |

## Key Improvements

| ID | Title | Target | Measured Impact | Status |
|----|-------|--------|----------------|--------|
| P1-1 | Fast-path `normalize()` | Hot-path allocation | -15% on uppercase input | KEEP |
| P1-2 | Reverse suffix index | O(n) suffix lookup | **296x faster** (5803 -> 19.6 ns/op) | KEEP |
| P1-3 | Cache synthetic records | Cold-path allocation | **3.3x faster** (52.4 -> 15.8 ns/op) | KEEP |
| P1-4 | Unmodifiable wrappers | Load-time memory | Init-time only, not measurable at runtime | KEEP |

## Completed Optimizations

### P1-1: Fast-path `normalize()` to avoid hot-path allocations -- KEEP
- **File**: `PhpStubs.kt`
- **Change**: Check for leading `/` or `\` before `substring`; skip `lowercase()` when input is already all-lowercase ASCII.
- **Measured**: -15% on uppercase input path (30.0 -> 25.6 ns/op). Common lowercase path within noise margin.

### P1-2: Reverse suffix index for O(1) method/constant lookup -- KEEP
- **File**: `PhpStubs.kt`
- **Change**: Lazily-built `methodSuffixIndex` and `classConstSuffixIndex` maps (suffix after `::` -> full key) via `buildSuffixIndex()`. `HashMap.containsKey`/`HashMap.get` for O(1) lookup.
- **Measured**: `containsMethod(name, null)` from 5803 -> 19.6 ns/op (**296x**). `searchMethod(name, null)` from 5916 -> 36.7 ns/op (**161x**).

### P1-3: Cache synthetic keyword/scalar StubRecord instances -- KEEP
- **File**: `PhpStubs.kt`
- **Change**: Pre-built `KEYWORD_RECORDS` and `SYNTHETIC_CLASS_RECORDS` maps. `searchFunc`/`searchClass` return cached instances.
- **Measured**: `searchFunc(keyword)` from 52.4 -> 15.8 ns/op (**3.3x**). Eliminates per-call allocation.

### P1-4: Unmodifiable wrappers instead of defensive copies -- KEEP
- **File**: `StubLoader.kt`
- **Change**: `Collections.unmodifiableMap` wraps mutable maps in `StubLoader.loadAll()` instead of copying.
- **Measured**: Reduces init-time memory spike. Not measurable at query time.

## Evaluated & Rejected

| ID | Title | Reason |
|----|-------|--------|
| P1-5 | StringBuilder for method key concat | SKIP -- Kotlin compiler optimizes string templates to StringBuilder. No measurable benefit. |

## Candidates

(empty -- round 1 complete)

## Remaining Known Bottlenecks

- `containsMethod -- with class` (46.6 ns/op) is 2.4x slower than `containsFunc` (19.2 ns/op) due to double `normalize()` + string concatenation for the composite key.
- `searchMethod -- with class` (61.3 ns/op) is the slowest operation -- double normalize + concat + HashMap lookup.
- YAML loading at startup: SnakeYAML parses 58 YAML files into Java objects, then maps to `StubRecord` subtypes. Lazy `StubRegistry` initialization defers this cost to first access.

## Key Insights

1. Read-only lookup library -- all data immutable after load. Optimization focus: allocation reduction and algorithmic complexity.
2. Main gains from reducing String allocations in normalize/lookup and replacing linear scans with HashMap.
3. Kotlin string templates (`"$a::$b"`) compile to `StringBuilder` -- manual StringBuilder offers no benefit.
4. `Collections.unmodifiableMap` wraps without copying, cheaper than `toMap()`.
5. `normalize()` fast-path benefits uppercase input only (-15%). JIT optimizes `String.lowercase()` for ASCII.
6. Cached synthetic records (16 ns/op) faster than registry lookup (23 ns/op) -- skips HashMap lookup.
7. Suffix-only method lookup (20 ns/op) faster than with-class lookup (47 ns/op) thanks to reverse index (P1-2).
8. Cross-test JIT contamination causes 5-25% variance. Only changes >30% or algorithmic improvements are reliably attributable.
9. Performance test class: `PhpStubsPerformanceTest` (`@Tag("performance")`). Run: `./gradlew test -Pperformance`. Default `./gradlew test` excludes performance tests. Ops/run: 100K, warmup: 5, measurement: 7 (median).
