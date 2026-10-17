# Documentation Index

| File | Topic |
|------|-------|
| [concept.md](concept.md) | Problem statement, data-side concepts over commons-phpmodels, extension provenance, scenarios |
| [concept-lookup.md](concept-lookup.md) | Canonical vocabulary, the merge, `BuiltinRecord` and `BuiltinLookup` by PHP name |
| [concept-extraction.md](concept-extraction.md) | Extraction from php-src: declarations, Handlers, Raises Summary, Boundary Call |
| [concept-taint.md](concept-taint.md) | The taint document set in psalm's names, its extraction, and its translation at the merge |
| [concept-taint-rules.md](concept-taint-rules.md) | The hand-maintained taint rules document set: Argus sink facts, added sanitizer facts and source facts, vocabulary additions |
| [concept-value-rules.md](concept-value-rules.md) | The hand-maintained value rules set: value units beyond the generated declarations, generated-set gaps |
| [model-lookup.md](model-lookup.md) | Bundled sets, canonical vocabulary, psalm mapping, merge order, merge, consumer sets, `BuiltinRecord`, Fact with condition, `BuiltinLookup` |
| [design.md](design.md) | `StubResources`, merge order, generated-set rules, resource layout, exception types |
| [design-extraction.md](design-extraction.md) | `php_src` and the php-src producers: hierarchy, signature, and throws extraction |
| [design-lookup.md](design-lookup.md) | `BuiltinLookup`, `PhpStubs`, `BuiltinRecord`, fact types, canonical enums |
| [design-merge.md](design-merge.md) | `Mount`, `MountSequence`, `Merge`: set mounting, failure classification, the fold |
| [design-taint.md](design-taint.md) | `StubResources`, taint resource layout, extraction script inputs and validation rules |
| [design-taint-rules.md](design-taint-rules.md) | `StubResources.TAINT_RULES`, rules resource layout, validation and maintenance rules |
| [design-value-rules.md](design-value-rules.md) | `StubResources.VALUE_RULES`, value rules resource layout, validation and maintenance rules |
| [spec-merge.md](spec-merge.md) | Folding the mounted sets into one statement per subject, condition, and unit |
| [spec-throws.md](spec-throws.md) | Computing the throws section from the php-src C sources: the Raises Summary fixpoint |
| [impl.md](impl.md) | commons-phpmodels API findings, version constraints, extension and set provenance, variadic, taint-extraction, and value rules review notes |
| [performance.md](performance.md) | Load-time and lookup benchmark procedure and baselines |
| [llms.txt](llms.txt) | Agent-facing L0 index (llmstxt.org format) |
| [llms/stubs.md](llms/stubs.md) | Agent-facing API reference: `BuiltinLookup`, `PhpStubs`, `BuiltinRecord`, facts, enums, `StubResources` |
| [llms/full.txt](llms/full.txt) | Agent-facing L2 concatenation of llms.txt and llms/stubs.md |
