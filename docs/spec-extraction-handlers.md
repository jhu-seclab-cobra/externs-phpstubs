# PHP Stubs — Effective Handler Extraction

## Effective Tables and Request Summaries

**Problem:** Read the source definitions and runtime class registrations of one
checkout and the source dispatch inventory. Produce the class signature's effective
table alternatives and per-request targets, positive absences, normal-result
kinds and string dispatch. Unknown source coverage remains unestablished.

**Steps:**

1. Read the existing stub declarations, C definitions, macros, registrations and
   source placement. Read registered flags without inferring FINAL from
   enum kind. Keep conditional-compilation alternatives rather than
   sequentially overwriting one configuration with another.
2. Resolve aggregate `zend_object_handlers` members by the struct declaration,
   including zero initialization. Evaluate direct struct assignment and memcpy
   as copies at that program point; later slot assignments replace the copied
   slot. A stored pointer observes the table contents when used, rather than
   freezing a pre-initialization snapshot. Retain distinct branch outcomes.
   A concrete NULL is positive absence;
   an unresolved value is not NULL.
3. Start at each class registration's default_object_handlers and create_object.
   Propagate class-entry defaults through engine initialization and inheritance;
   follow reachable allocation, clone, factory and lifetime writes of the object
   handlers field. Trace arguments and locals to the tables they denote. Emit
   every reachable effective table, including a named alternative with partial
   facts or an unresolved alternative. Do not select by unmodeled object state.
4. For each resolved present slot and consumed request, extend the existing C
   procedure-summary mechanism with typed member flow, request tests, output
   writes and return status. Join branch outcomes and direct-call summaries to
   a fixpoint. Resolve the registered class's effective method declarations
   when summarizing standard dispatch, so a class without a string method
   has no invented normal string result. Hypothetical user-subclass methods
   are served by the dispatch descriptor and ordinary call, not by erasing
   that class-specific proof. Track exceptions separately from normal success.
5. Classify the output at a normal SUCCESS exit, after all writes and conversion
   calls. An intermediate output type or a sentinel returned with a pending
   exception is not a normal-result kind. A complete proof of no normal exit
   emits an empty set; an incomplete proof omits the fact. COMPARE's normal C
   return is NUM, independently of the comparison expression's result type.
6. Derive the string dispatch order from the relative reachability of the
   effective-method call, native work, success exits and failure continuation.
   The standard dispatcher supplies the effective __toString call. Native
   conversion failure and an earlier native-invocation failure are distinct.
   An unsupported mandatory control-flow form fails extraction; explicitly
   admitted unavailable coverage leaves the request unestablished.
7. Derive consumed tokens from engine sites and forwarded macro arguments;
   validate their names and slot partitions through commons-phpmodels, with
   no Python whitelist or Kotlin-source parser. Runtime
   truth requests use _IS_BOOL; arithmetic numeric conversion uses _IS_NUMBER.
   Plain and compound operators use the underlying opcode. Both unary signs
   use ZEND_MUL; increment and decrement use ZEND_ADD and ZEND_SUB. Runtime
   boolean not requests truth; runtime xor can request ZEND_BOOL_XOR. Structural
   array/object casts do not themselves request cast_object. Standard mixed
   comparison may request IS_ARRAY or IS_RESOURCE. Deferred constant-expression
   logical not can request ZEND_BOOL_NOT through the unary-operation API.
8. Validate and emit complete immutable class signatures through the existing
   placement and field-preserving writer. Replace classifier, parent,
   interfaces, isFinal and handlers from source; preserve every unowned
   field and unrelated byte. Recompute owned facts instead of retaining stale
   generated facts. The entire signature stays one override unit. Account
   for every source selection/write and unestablished subject/table/request.

**Invariants:** Only reachable tables contribute facts; copies obey C write
order; every source alternative contributes; every emitted normal bound covers
all normal exits; absence and missing coverage are never joined into one flag.

**Termination:** The source identities, lvalue paths, table fields, request
values, output kinds, success/failure statuses, pending-exception states and
four dispatch orders form finite summary domains. Guards use source branch
identities, never arbitrary native predicates. Alias and direct-call transfers
grow summaries monotonically per recursive component. Unsupported mandatory
expressions fail instead of introducing unbounded paths or guessed results.

**Complexity:** For S input bytes, W actual transfer and set-processing work,
and R output items, time is O(S + W + R log R); space is the source/indexes,
live guarded summary states and output. W includes fixpoint revisits and branch
combinations, which may be exponential. This is offline generation, with no
claimed source-linear bound or additional interpretation-phase traversal.

**Edge cases:** Whole standard-table copies, overwritten slots, explicit NULL,
conditional compilation, shared allocators, inherited defaults, state-dependent
table changes, output conversion after a write, failure with a PHP fallback,
method-first and native-first dispatch, pending exceptions and external classes
are tested through the same rules.
