# externs-phpstubs Performance

## Current Baseline

Measured on: 2026-09-01 | JVM: JDK 21 | Registry: commons-phpmodels entries (commit f2d4358)
Benchmark: `./gradlew test -Pperformance` | Warmup: 5 runs | Measurement: 7 runs (median)
Dataset: 5,694 subjects (5,335 functions + 115 classes + 2 methods + 242 constants) over 61 documents

### Hot Path -- Existence Checks (100K ops/run)

| Operation | Median (ms) | ns/op | Throughput (ops/s) |
|-----------|------------|-------|-------------------|
| containsFunction -- known | 2.75 | 27.5 | 36,422,136 |
| containsFunction -- unknown | 3.29 | 32.9 | 30,352,081 |
| containsFunction -- keywords | 3.14 | 31.4 | 31,854,742 |
| containsFunction -- uppercase | 4.53 | 45.3 | 22,095,580 |
| containsFunction -- namespace prefix | 3.67 | 36.7 | 27,252,902 |
| containsClass -- known | 3.02 | 30.2 | 33,094,326 |
| containsClass -- scalar types | 2.90 | 29.0 | 34,513,999 |
| containsMethod -- with class | 5.36 | 53.6 | 18,650,046 |
| containsMethod -- suffix only | 1.51 | 15.1 | 66,143,034 |
| containsConstant | 2.63 | 26.3 | 37,954,870 |

### Cold Path -- Entry Retrieval (100K ops/run)

| Operation | Median (ms) | ns/op | Throughput (ops/s) |
|-----------|------------|-------|-------------------|
| findFunction -- known | 2.76 | 27.6 | 36,249,404 |
| findFunction -- keywords | 2.91 | 29.1 | 34,333,290 |
| findClass -- scalar types | 2.82 | 28.2 | 35,433,764 |
| findMethod -- with class | 3.90 | 39.0 | 25,621,592 |
| findMethod -- suffix only | 1.53 | 15.3 | 65,441,428 |

### Memory

| Metric | Value |
|--------|-------|
| Heap after full load | 35.89 MB |
| Total subjects | 5,694 |

## Comparison With the Previous Registry (2026-03-24)

The former registry keyed hand-normalised strings over `StubRecord` values; the current one keys commons-phpmodels subjects over decoded `SubjectModel` entries. Every lookup now allocates one subject (creator: strip `\`, validate, fold), which costs 8-16 ns/op on the hot path; suffix-only member lookups fold a plain string and are faster than before. Heap grew from 15.71 MB to 35.89 MB: each entry retains the full decoded model (signature objects, parameter lists, body sections) instead of a flat record, and the old dataset counted 22,477 keys because it indexed methods and constants the generated corpus does not carry (methods: 9,872 then, 2 now).

## Optimization Ledger

| ID | Title | Status |
|----|-------|--------|
| P1-1 | Fast-path `normalize()` | RETIRED -- name handling moved into the commons-phpmodels subject creators |
| P1-2 | Reverse suffix index | KEEP -- `methodSuffixIndex`, `classConstSuffixIndex` and folded companions in `PhpStubs.kt` |
| P1-3 | Cache synthetic records | RETIRED -- language constructs are data under `models/language/`, no synthetic records exist |
| P1-4 | Unmodifiable wrappers | KEEP -- `Collections.unmodifiableMap` in `StubLoader.freeze()` |
| P1-5 | StringBuilder for member key concat | SKIP -- Kotlin string templates already compile to `StringBuilder` |

## Candidates

- Subject allocation per lookup: a creator-level fast path for already-folded ASCII names belongs in commons-phpmodels, not here.
- Load-time heap: `ParameterInfo` lists are the largest retained structure; interning `DeclaredType` values across entries would cut duplicates of `string`, `int`, `mixed`.

## Remaining Known Bottlenecks

- `containsMethod -- with class` (53.6 ns/op) builds a `MethodSubject` through `ClassSubject.parse` plus the member constructor: two folds per call.
- Decode at startup: 61 documents through Jackson YAML into validated entries; the lazy registry defers this to first access.

## Key Insights

1. Read-only lookup library -- all data immutable after load. Optimization focus: allocation per lookup and retained size per entry.
2. Cross-test JIT contamination causes 5-25% variance. Only changes >30% or algorithmic improvements are reliably attributable.
3. Performance test class: `PhpStubsPerformanceTest` (`@Tag("performance")`). Run: `./gradlew test -Pperformance`. Default `./gradlew test` excludes performance tests. Ops/run: 100K, warmup: 5, measurement: 7 (median).
