# externs-phpstubs Performance

## Current Baseline

No benchmark infrastructure yet. Optimizations identified and applied via static code analysis.

## Key Improvements

| ID | Title | Target | Impact | Status |
|----|-------|--------|--------|--------|
| P1-1 | Fast-path `normalize()` | Hot-path allocation | Avoid 2 String allocs per query when input is already lowercase ASCII | KEEP |
| P1-2 | Reverse suffix index | O(n) → O(1) suffix lookup | HashMap lookup replaces linear scan over ~10K+ method/constant keys | KEEP |
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

### P1-3: Cache synthetic keyword/scalar StubRecord instances
- **File**: `PhpStubs.kt`
- **Change**: Pre-built `KEYWORD_RECORDS` and `SYNTHETIC_CLASS_RECORDS` maps. `searchFunc`/`searchClass` return cached instances.
- **Impact**: Zero allocation on repeated lookups for 15 keywords + 5 scalar types + 2 special types.

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

- Deserialization via `DftByteArraySerializerImpl.deserialize()` is the dominant cost on cold-path lookups. Optimization depends on commons-value internals.
- `getAll()` forces eager deserialization of entire sections.

## Key Insights

1. This is a read-only lookup library — all data is immutable after load. Optimization focus is on allocation reduction and algorithmic complexity for lookups.
2. Two-tier architecture already avoids deserialization on hot path; main gains come from reducing String allocations in normalize/lookup.
3. Kotlin string templates (`"$a::$b"`) compile to `StringBuilder` — manual StringBuilder offers no benefit.
4. `Collections.unmodifiableSet/Map` is cheaper than `toSet()`/`toMap()` for preventing mutation of internal collections, as it wraps without copying.
