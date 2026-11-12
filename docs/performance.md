# externs-phpstubs — performance checks

## Method

Run tagged measurements with `./gradlew test -Pperformance`; default tests exclude the performance tag. Separate cold set loading from repeated exact lookup and pattern-query traversal. Report warmup, measurement count, JDK, heap settings, resource counts and variation for the measured revision.

## Workloads

Measure known/absent function, class, member and constant queries separately. Include the qualified-member spelling and split owner/member APIs. Pattern workloads include broad matches and broad negative queries; first-result and complete enumeration are separate measurements.

## Bounds

[Set Merge](spec-merge.md#complexity) specifies loading/assembly bounds; [canonical-name query](spec-merge.md#canonical-name-query) specifies trie construction and query state. Heap measurements distinguish retained records, declarations, Facts and query state; an older resource count does not describe a different input set.
