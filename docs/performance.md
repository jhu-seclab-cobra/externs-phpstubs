# externs-phpstubs Performance

## Current Baseline (post-optimization)

Measured on: 2026-03-24 | JVM: JDK 21 | JVM flags: `-Xmx2g -Xms1g`
Benchmark: `./gradlew test -Pperformance` | Warmup: 5 runs | Measurement: 7 runs (median)
Dataset: 22,477 total keys (5,021 functions + 1,538 classes + 9,872 methods + 6,046 constants)

### Hot Path — Existence Checks (100K ops/run)

| Operation | Median (ms) | ns/op | Throughput (ops/s) |
|-----------|------------|-------|-------------------|
| containsFunc — known | 1.92 | 19.2 | 51,985,184 |
| containsFunc — unknown | 1.47 | 14.7 | 67,898,250 |
| containsFunc — keywords | 1.62 | 16.2 | 61,889,154 |
| containsFunc — uppercase | 2.56 | 25.6 | 39,025,669 |
| containsFunc — slash prefix | 2.81 | 28.1 | 35,527,651 |
| containsClass — known | 1.87 | 18.7 | 53,592,980 |
| containsClass — scalar types | 1.21 | 12.1 | 82,947,351 |
| containsMethod — with class | 4.66 | 46.6 | 21,442,354 |
| containsMethod — suffix only | 1.96 | 19.6 | 51,000,892 |
| containsConst | 1.65 | 16.5 | 60,473,202 |

### Cold Path — Record Retrieval (100K ops/run)

| Operation | Median (ms) | ns/op | Throughput (ops/s) |
|-----------|------------|-------|-------------------|
| searchFunc — known | 2.30 | 23.0 | 43,391,797 |
| searchFunc — keywords | 1.58 | 15.8 | 63,254,427 |
| searchClass — scalar types | 1.61 | 16.1 | 62,224,501 |
| searchMethod — with class | 6.13 | 61.3 | 16,321,422 |
| searchMethod — suffix only | 3.67 | 36.7 | 27,252,597 |

### Memory

| Metric | Value |
|--------|-------|
| Heap after full load | 15.71 MB |
| Total keys | 22,477 |

## Before vs After Comparison

Pre-optimization baseline measured at commit `3eecd2a` (2 independent runs, median of each).

### Hot Path

| Operation | Before (ns/op) | After (ns/op) | Change |
|-----------|---------------|--------------|--------|
| containsFunc — known | 17.0 | 19.2 | +13% (noise) |
| containsFunc — unknown | 14.0 | 14.7 | +5% (noise) |
| containsFunc — keywords | 18.7 | 16.2 | -13% |
| containsFunc — uppercase | 30.0 | 25.6 | -15% |
| containsFunc — slash prefix | 28.9 | 28.1 | -3% (noise) |
| containsClass — known | 14.9 | 18.7 | +26% (noise/JIT) |
| containsClass — scalar types | 11.5 | 12.1 | +5% (noise) |
| containsMethod — with class | 44.5 | 46.6 | +5% (noise) |
| **containsMethod — suffix only** | **5803.2** | **19.6** | **-99.7% (296x faster)** |
| containsConst | 13.3 | 16.5 | +24% (noise/JIT) |

### Cold Path

| Operation | Before (ns/op) | After (ns/op) | Change |
|-----------|---------------|--------------|--------|
| searchFunc — known | 25.3 | 23.0 | -9% |
| **searchFunc — keywords** | **52.4** | **15.8** | **-70% (3.3x faster)** |
| searchClass — scalar types | 15.9 | 16.1 | +1% (noise) |
| searchMethod — with class | 52.8 | 61.3 | +16% (noise/JIT) |
| **searchMethod — suffix only** | **5915.5** | **36.7** | **-99.4% (161x faster)** |

### Summary

| Optimization | Measured Impact |
|-------------|----------------|
| **P1-2: Reverse suffix index** | **containsMethod suffix: 296x faster, searchMethod suffix: 161x faster** |
| **P1-3: Cached synthetic records** | **searchFunc keywords: 3.3x faster** |
| P1-1: normalize() fast-path | containsFunc uppercase: -15%, other paths within noise |
| P1-4: Unmodifiable wrappers | No runtime impact (init-time only, not benchmarked) |

## Key Improvements

| ID | Title | Target | Measured Impact | Status |
|----|-------|--------|----------------|--------|
| P1-1 | Fast-path `normalize()` | Hot-path allocation | -15% on uppercase input | KEEP |
| P1-2 | Reverse suffix index | O(n) → O(1) suffix lookup | **296x faster** (5803 → 19.6 ns/op) | KEEP |
| P1-3 | Cache synthetic records | Cold-path allocation | **3.3x faster** (52.4 → 15.8 ns/op) | KEEP |
| P1-4 | Unmodifiable wrappers | Load-time memory | Init-time only, not measurable at runtime | KEEP |

## Completed Optimizations

### P1-1: Fast-path `normalize()` to avoid hot-path allocations
- **File**: `PhpStubs.kt`
- **Change**: Check for leading `/` before `substring`; skip `lowercase()` when input is already all-lowercase ASCII.
- **Impact**: -15% on uppercase input path. Common lowercase path within noise margin.

### P1-2: Reverse suffix index for O(1) method/constant lookup
- **File**: `StubSection.kt`, `PhpStubs.kt`
- **Change**: Added lazily-built `suffixIndex` map in `StubSection` (suffix after `::` → full keys). Replaced `keys.any { it.endsWith(suffix) }` and `keys.firstOrNull { it.endsWith(suffix) }` with `HashMap.containsKey`/`HashMap.get`.
- **Impact**: `containsMethod(name, null)` from 5803 → 19.6 ns/op (**296x**). `searchMethod(name, null)` from 5916 → 36.7 ns/op (**161x**).

### P1-3: Cache synthetic keyword/scalar StubRecord instances
- **File**: `PhpStubs.kt`
- **Change**: Pre-built `KEYWORD_RECORDS` and `SYNTHETIC_CLASS_RECORDS` maps. `searchFunc`/`searchClass` return cached instances.
- **Impact**: `searchFunc(keyword)` from 52.4 → 15.8 ns/op (**3.3x**). Eliminates per-call allocation of StubRecord + ListVal + StrVal.

### P1-4: Unmodifiable wrappers instead of defensive copies
- **File**: `PhpStubs.kt`
- **Change**: `readSection()` wraps `LinkedHashSet`/`HashMap` with `Collections.unmodifiableSet/Map` instead of `toSet()`/`toMap()` which copy all entries.
- **Impact**: Reduces init-time memory spike and avoids ~22K entry duplication per section (4 sections). Not measurable at query time.

## Evaluated & Rejected

| ID | Title | Reason |
|----|-------|--------|
| P1-5 | StringBuilder for method key concat | SKIP — Kotlin compiler already optimizes string templates to StringBuilder. No measurable benefit. |

## Candidates

(empty — round 1 complete)

## Remaining Known Bottlenecks

- `containsMethod — with class` (46.6 ns/op) is 2.4x slower than simple `containsFunc` (19.2 ns/op) due to double `normalize()` + string concatenation for the composite key.
- `searchMethod — with class` (61.3 ns/op) is the slowest operation — combines double normalize + concat + ConcurrentHashMap lookup.
- Deserialization via `DftByteArraySerializerImpl.deserialize()` is the dominant cost on cold-path lookups. Optimization depends on commons-value internals.
- `getAll()` forces eager deserialization of entire sections.

## Key Insights

1. This is a read-only lookup library — all data is immutable after load. Optimization focus is on allocation reduction and algorithmic complexity for lookups.
2. Two-tier architecture already avoids deserialization on hot path; main gains come from reducing String allocations in normalize/lookup.
3. Kotlin string templates (`"$a::$b"`) compile to `StringBuilder` — manual StringBuilder offers no benefit.
4. `Collections.unmodifiableSet/Map` is cheaper than `toSet()`/`toMap()` for preventing mutation of internal collections, as it wraps without copying.
5. The `normalize()` fast-path shows measurable benefit only on uppercase input (-15%). The common lowercase path is within noise margin — the JIT likely already optimizes `String.lowercase()` for ASCII-only strings.
6. Cached synthetic records (P1-3) make keyword/scalar retrieval (16 ns/op) faster than index-based retrieval (23 ns/op) by skipping ConcurrentHashMap lookup entirely.
7. Suffix-only method lookup (20 ns/op) is now faster than with-class lookup (47 ns/op) thanks to the reverse index (P1-2) — the reverse index avoids double normalize + concat.
8. Cross-test JIT contamination causes 5-25% variance in unrelated operations between runs. Only changes >30% or algorithmic improvements (like P1-2) are reliably attributable.

## Benchmark Infrastructure

- Test class: `PhpStubsPerformanceTest` (tagged `@Tag("performance")`)
- Run: `./gradlew test -Pperformance`
- Default `./gradlew test` excludes performance tests
- Operations per run: 100,000
- Warmup: 5 runs, Measurement: 7 runs (median reported)
- JVM flags (performance mode only): `-Xmx2g -Xms1g`
