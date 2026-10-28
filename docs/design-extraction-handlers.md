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
- Handler summaries extend the existing summary mechanism with the finite
  data named by the extraction specification; they are offline working data,
  never a second runtime handler store.
- The machine bounds its working states without dropping an outcome. States
  that reach one join point with the same event history and pending exception
  are joined into one whose differing cells are alternatives; outcomes of one
  expression whose states are equal become one outcome whose value is the
  alternatives of their values; the exits of a call with one history are
  joined the same way. A call that exceeds its step or pending-state budget
  yields no summary, so its facts are omitted, never emitted empty.

## Function Specifications

- `read_handler_tables(program, declarations)` — produces table groups through
  the extraction specification, preserving every admitted unknown alternative.
- `Entry.with_signature(block, owned_fields)` — replaces only the explicitly
  owned keys and inserts a missing signature; preserves every unowned field
  and every other entry byte, including comments, nested values and EOF.
  The hierarchy producer owns classifier, parent, interfaces, isFinal and
  handlers for registered source declarations; stub-only declarations retain
  hierarchy treatment but establish no registered finality or handler table.
- Hierarchy regeneration recomputes owned generated facts from source; an
  old generated handler value is not evidence for preserving it unchanged.
  Source-external entries keep their existing fields and bytes.
- Source summaries use the registered class's effective methods; hypothetical
  descendant methods remain ordinary calls admitted by the dispatch descriptor.
- Consumed tokens come from the source dispatch inventory. The generated-set
  decode gate checks the single PM enum; the producer has no allowed-name
  list and no dependency on the consumer's internal operator vocabulary.

## Exception / Error Types

- `ExtractionFailure`: malformed or conflicting declarations, unclassified
  mandatory writes/selections, unresolved mandatory targets/result paths,
  or a changed/unreadable admitted semantic primitive.
- Deliberately unavailable external coverage remains missing; COM's absence
  in one build does not erase its source-backed facts.
