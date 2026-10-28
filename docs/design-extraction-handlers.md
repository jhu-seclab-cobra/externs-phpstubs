# PHP Stubs — Handler Extraction Design

The handler concern of [Hierarchy Extraction](design-extraction.md).
Algorithm: [Effective Handler Extraction](spec-extraction-handlers.md).
Format: [handler types](../../commons-phpmodels/docs/design-declarations-handlers.md).

## Design Overview

- **Modules:** `php_src`, `php_src_c`, `extract_hierarchy`, and the handler
  modules, one per stage of the extraction: `handler_memory` and
  `handler_values` (abstract memory and values), `handler_index`,
  `handler_expr`, `handler_machine`, `handler_prims` and `handler_world` (the
  machine that runs C bodies), `handler_requests` (the requests the engine
  makes), `handler_minit` (class registration), `handler_create` (object
  creation), `handler_summary` (request summaries), `handler_sites`, `handler_tables`
  and `handler_render` (write-site dispositions, table alternatives, the
  rendered field), and `handler_facts` (the driver).
- **Relationships:** tools import the shared `php_src` surface, which imports
  no producer. The C source/macro/definition/registration reader moves from
  `extract_throws` to `php_src_c`; it is not copied. The handler modules extend
  the existing procedure-summary mechanism for this extraction concern, and
  only `handler_facts` and `extract_hierarchy` are entry points of other tools.
- **Dependency roles:** shared source identity, parsing and registrations belong
  to the reader; table/result extraction belongs to the hierarchy producer;
  throws semantics remain with the throws producer; YAML validation belongs
  to commons-phpmodels. The complete signature remains one override unit.
- **Errors:** the existing `ExtractionFailure` names source and subject.

## Class / Type Specifications

- Source, macro, definition and registration values are shared reader data.
  Reader extension preserves branch provenance instead of imposing a
  last-write order on mutually exclusive configurations. The throws view
  retains its decided boundaries and output.
- Each definition retains its enclosing conditional-compilation provenance.
  A handler target summarizes every matching definition; all of their normal
  exits contribute, and an incomplete alternative leaves the request unknown.
- Handler summaries extend the existing summary mechanism with the finite
  data named by the extraction specification; they are offline working data,
  never a second runtime handler store. `php_src_c.definitions.ProcedureSummaries`
  owns the callee-first SCC iteration and completed-result table for both
  producers. C no-return declarations have no normal exit; source sizes
  compare by type name. The throws evaluator supplies its existing domain; the handler
  evaluator supplies guarded return/memory-effect alternatives. `Summarizer`
  classifies request exits and has no separate summary cache.
  New direct-call inputs use the shared driver's explicit continuation stack.
  The caller suspends at its current instruction while a new callee settles;
  retry restores that instruction's state and lexical bindings, without
  rerunning completed instructions. An acyclic input with settled callees is
  completed immediately; recursive inputs retain the current outcome set
  until component iteration stabilizes. A permanently incomplete
  outcome releases its dependencies, and unfinished unreachable inputs are
  discarded rather than cached as completed results.
- Handler procedure inputs retain globals and the memory reachable from their
  arguments. Reachable local and allocated regions are renamed by argument
  position, preserving aliases. Effects are renamed back onto the current
  caller; unrelated caller locals are never read from a cached summary.
  Sizes and aggregate values have value identity. Conditional aggregate
  copies join each member with its source guards. Unknown calls invalidate
  canonical argument locations just as they invalidate caller locations.
- The machine bounds its working states without dropping an outcome. States
  that reach one join point with the same event history and pending exception
  are joined into one whose differing cells are alternatives; outcomes of one
  expression whose states are equal become one outcome whose value is the
  alternatives of their values; the exits of a call with one history are
  joined the same way. A call that exceeds its step or pending-state budget
  yields no summary, so its facts are omitted, never emitted empty.
  Value alternatives, binary operand combinations and called definitions are
  processed in full; batching chooses joins and never discards a remainder.
  Direct-call evaluation retains the machine's existing step slice and
  unknown-call transfer when that slice is exhausted. A later proved write
  can establish an output; the unknown transfer alone establishes no kind.
  Total request exhaustion discards unfinished summaries.

## Function Specifications

- `read_handler_tables(program, declarations)` — produces table groups through
  the extraction specification, preserving every admitted unknown alternative.
- `Entry.with_signature(block, owned_fields)` — replaces only the explicitly
  owned keys and inserts a missing signature; preserves every unowned field
  and every other entry byte, including comments, nested values and EOF.
  Signature-level comments and blank lines between fields are unowned spans;
  replacing or removing an owned field retains those spans in place.
  The hierarchy producer owns classifier, parent, interfaces, isFinal and
  handlers for registered source declarations; stub-only declarations retain
  hierarchy treatment but establish no registered finality or handler table.
- Hierarchy regeneration recomputes owned generated facts from source; an
  old generated handler value is not evidence for preserving it unchanged.
  Source-external entries keep their existing fields and bytes.
- An unresolved output type or a successful exit without a proved output
  leaves the request unestablished. ANY requires a known non-scalar tag or
  an output derived from an operand or effective method, not unread analysis.
- Source summaries use the registered class's effective methods; hypothetical
  descendant methods remain ordinary calls admitted by the dispatch descriptor.
- A comparison request can close its NUM bound after a proved normal exit:
  the C return protocol excludes every other kind. This request projection
  has a distinct key from a callee's complete return/effect summary, and its
  early closure discards unfinished callees. Opaque instructions prevent
  early closure, including opacity in nested statement expressions. The source
  index carries that property from the existing parsed body into its compiled
  representation. Proving no normal exit still requires the full fixpoint.
- Consumed tokens come from the source dispatch inventory. The generated-set
  decode gate checks the single PM enum; the producer has no allowed-name
  list and no dependency on the consumer's internal operator vocabulary.

## Exception / Error Types

- `ExtractionFailure`: malformed or conflicting declarations, unclassified
  mandatory writes/selections, unresolved mandatory targets/result paths,
  or a changed/unreadable admitted semantic primitive.
- Deliberately unavailable external coverage remains missing; COM's absence
  in one build does not erase its source-backed facts.
