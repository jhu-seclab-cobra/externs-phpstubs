# externs-phpstubs Performance

## Current Baseline

No benchmark infrastructure yet. Optimization candidates identified via static code analysis.

## Key Improvements

| ID | Title | Target | Impact | Status |
|----|-------|--------|--------|--------|

## Completed Optimizations

(none yet)

## Evaluated & Rejected

| ID | Title | Reason |
|----|-------|--------|

## Candidates

### P1-1: Eliminate `normalize()` hot-path allocations
- **File(s)**: `PhpStubs.kt`
- **Priority**: High
- **Hypothesis**: Every `containsFunc`/`containsClass` call invokes `lowercase().removePrefix("/")` — two String allocations per call. Pre-normalizing keys at load time makes hot-path existence checks zero-allocation. Only the input string needs `normalize()` at query time (unavoidable), but `removePrefix` can be skipped if keys are already stored without leading `/`.
- **Risk**: Low

### P1-2: O(n) suffix scan → reverse index
- **File(s)**: `PhpStubs.kt` (containsMethod, searchMethod, searchClassConst)
- **Priority**: High
- **Hypothesis**: `keys.any { it.endsWith(suffix) }` is a linear scan over all method/constant keys. A precomputed reverse index (`methodName → List<fullKey>`) makes suffix lookups O(1).
- **Risk**: Medium — adds memory for the reverse index

### P1-3: Cache synthetic keyword/scalar records
- **File(s)**: `PhpStubs.kt` (searchFunc, searchClass)
- **Priority**: Medium
- **Hypothesis**: `searchFunc("echo")` creates a new `StubRecord(ListVal(StrVal("keyword")))` on every call. Caching these as static vals eliminates repeated allocation for a fixed set of 15 keywords + 5 scalars + 2 special types.
- **Risk**: Low

### P1-4: Eliminate intermediate collection copies in `readSection`
- **File(s)**: `PhpStubs.kt` (readSection)
- **Priority**: Medium
- **Hypothesis**: `keys.toSet()` and `rawData.toMap()` create defensive copies of already-internal collections. Using `Collections.unmodifiableSet/Map` wrappers avoids duplicating ~22K entries at load time.
- **Risk**: Low

### P1-5: StringBuilder for method key concatenation
- **File(s)**: `PhpStubs.kt` (containsMethod, searchMethod)
- **Priority**: Low
- **Hypothesis**: `"${className.normalize()}::${methodName.normalize()}"` allocates via string template. Minor savings with pre-sized StringBuilder.
- **Risk**: Low

## Remaining Known Bottlenecks

- Deserialization via `DftByteArraySerializerImpl.deserialize()` is the dominant cost on cold-path lookups. Optimization depends on commons-value internals.
- `getAll()` forces eager deserialization of entire sections.

## Key Insights

1. This is a read-only lookup library — all data is immutable after load. Optimization focus is on allocation reduction and algorithmic complexity for lookups.
2. Two-tier architecture already avoids deserialization on hot path; main gains come from reducing String allocations in normalize/lookup.
