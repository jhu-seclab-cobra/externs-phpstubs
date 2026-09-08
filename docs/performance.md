# externs-phpstubs Performance

## Current Baseline

Measured on: 2026-09-08 | JVM: JDK 21 | Lookup: `PhpStubs` over the five-set merge (commit 3013f25)
Benchmark: `./gradlew test -Pperformance` | Warmup: 5 runs | Measurement: 7 runs (median)
Dataset: 5,764 records (5,349 functions + 115 classes + 58 methods + 242 constants) holding 5,936 facts over 97 documents

### Exact Lookup (100K ops/run)

| Operation | Median (ms) | ns/op | Throughput (ops/s) |
|-----------|------------|-------|-------------------|
| function -- known | 5.33 | 53.3 | 18,759,821 |
| function -- unknown | 7.46 | 74.6 | 13,396,222 |
| function -- keywords | 5.33 | 53.3 | 18,764,074 |
| function -- uppercase | 7.77 | 77.7 | 12,868,356 |
| function -- namespace prefix | 6.85 | 68.5 | 14,594,634 |
| clazz -- known | 5.54 | 55.4 | 18,066,165 |
| clazz -- scalar types | 4.59 | 45.9 | 21,786,098 |
| method -- qualified spelling | 12.25 | 122.5 | 8,164,903 |
| method -- owner and name | 12.85 | 128.5 | 7,780,108 |
| constant | 4.88 | 48.8 | 20,501,428 |

### Memory

| Metric | Value |
|--------|-------|
| Heap after the bundled merge | 38.66 MB |
| Total records | 5,764 |
| Total facts | 5,936 |

## Comparison With the Retired Registry (2026-09-01)

The retired `contains*`/`find*` facade read the generated set alone (5,694 subjects, 35.89 MB) at 27-54 ns/op. The lookup now reads the five-set merge: the same subject allocation per call, one `LinkedHashMap` get per kind, and a `BuiltinRecord` holding facts instead of a bare model. Function and constant lookups measure 49-78 ns/op and qualified method lookups 122-129 ns/op (`MethodSubject.parse` splits and folds two names); the retired suffix-only method index is gone. Heap grew by 2.8 MB for the vocabulary, taint, taint rules, and value rules sets folded into records.

## Optimization Ledger

| ID | Title | Status |
|----|-------|--------|
| P1-1 | Fast-path `normalize()` | RETIRED -- name handling moved into the commons-phpmodels subject creators |
| P1-2 | Reverse suffix index | RETIRED -- exact lookup only; a looser match is the consumer's filter over an enumeration |
| P1-3 | Cache synthetic records | RETIRED -- language constructs are data under `models/language/`, no synthetic records exist |
| P1-4 | Unmodifiable wrappers | KEEP -- the per-kind record maps of `Merge` are frozen once at construction |
| P1-5 | StringBuilder for member key concat | SKIP -- Kotlin string templates already compile to `StringBuilder` |

## Candidates

- Subject allocation per lookup: a creator-level fast path for already-folded ASCII names belongs in commons-phpmodels, not here.
- Load-time heap: `ParameterInfo` lists are the largest retained structure; interning `DeclaredType` values across entries would cut duplicates of `string`, `int`, `mixed`.

## Remaining Known Bottlenecks

- `method -- qualified spelling` (122.5 ns/op) parses `Owner::name` and folds both halves; `method -- owner and name` (128.5 ns/op) folds the owner through `ClassSubject.parse` and the name through the member constructor.
- Decode at startup: every bundled document through Jackson YAML into validated entries, then the fold; the bundled merge is built on first access to `PhpStubs`.

## Key Insights

1. Read-only lookup library -- all data immutable after load. Optimization focus: allocation per lookup and retained size per entry.
2. Cross-test JIT contamination causes 5-25% variance. Only changes >30% or algorithmic improvements are reliably attributable.
3. Performance test class: `PhpStubsPerformanceTest` (`@Tag("performance")`). Run: `./gradlew test -Pperformance`. Default `./gradlew test` excludes performance tests. Ops/run: 100K, warmup: 5, measurement: 7 (median).
