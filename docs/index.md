# Documentation Index

| File | Topic |
|------|-------|
| [concept.md](concept.md) | Problem statement, data-side concepts over commons-phpmodels, extension provenance, scenarios |
| [concept-lookup.md](concept-lookup.md) | Canonical vocabulary, the merge, Built-in Record and Built-in Lookup by PHP name |
| [concept-taint.md](concept-taint.md) | The taint document set in psalm's names, its extraction, and its translation at the merge |
| [concept-taint-rules.md](concept-taint-rules.md) | The hand-maintained taint rules document set: Argus sinks, added escapes and sources, vocabulary additions |
| [concept-value-rules.md](concept-value-rules.md) | The hand-maintained value rules set: value semantics beyond the generated declarations, corpus gaps |
| [model-lookup.md](model-lookup.md) | Bundled sets, canonical vocabulary, psalm mapping, merge order, extension sets, Built-in Record, Fact, Built-in Lookup |
| [design.md](design.md) | Entry, registry, loader, and facade specifications; resource layout; corpus rules; exception types |
| [design-taint.md](design-taint.md) | `StubResources`, taint resource layout, extraction script inputs and validation rules |
| [design-taint-rules.md](design-taint-rules.md) | `StubResources.TAINT_RULES`, rules resource layout, validation and maintenance rules |
| [design-value-rules.md](design-value-rules.md) | `StubResources.VALUE_RULES`, value rules resource layout, validation and maintenance rules |
| [impl.md](impl.md) | commons-phpmodels API findings, version constraints, extension and set provenance, variadic, taint-extraction, and value rules review notes |
| [performance.md](performance.md) | Load-time and lookup benchmark procedure and baselines |
| [llms.txt](llms.txt) | Agent-facing L0 index (llmstxt.org format) |
| [llms/stubs.md](llms/stubs.md) | Agent-facing API reference for the stubs registry, taint sets, and value rules set |
| [llms/full.txt](llms/full.txt) | Agent-facing L2 concatenation of llms.txt and llms/stubs.md |
