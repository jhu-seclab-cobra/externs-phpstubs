# PHP Stubs — Raises Algorithm

Computing the raises section of every implemented built-in from the php-src
C sources. Concepts: [concept-extraction.md](concept-extraction.md)
(Handler, Raises Summary, Boundary Call). Tool structure and tables:
[design-extraction.md](design-extraction.md). What a raises section
asserts: commons-phpmodels `docs/model.md`.

## Algorithm: Raises Summary Fixpoint

### Problem

Input: the definitions of one php-src checkout — C functions, handler
macro definitions, function-like macros — and the built-in entries with
their Handlers. Output: per entry, the set of exception classes its
Handlers may throw outside the Boundary Calls, or *open* when a Handler
throws an object no class set bounds. Correctness: every class a direct
call chain from a Handler can throw through a throwing primitive is in the
set; a call through a function pointer is not followed
([design-extraction.md](design-extraction.md) Open Gaps).

A *term* is one of `class(C)`, `class_param(i, default)` (the class entry
the caller passes as parameter `i`), `object_param(i)` (the object the
caller passes), or `open`, each with a guard set of `(parameter, truth)`
pairs. A Raises Summary is `(raises: terms, creates: parameter → class
terms, returns: class terms)`.

### Steps

```
raises(definitions, entries):
    roots = { d : d defines a Handler of some entry }
    graph = reachable(roots)                      # direct calls and function names used as values
    summaries = {}                                # definition → Summary, initially empty
    for component in tarjan(graph), callees first:
        repeat
            for d in component: summaries[d] = evaluate(d, summaries)
        until no summary changed
    for entry in entries:
        terms = ∪ summaries[h].raises for h in entry.handlers
        entry.result = open if a term is open else { C : class(C) ∈ terms }

evaluate(d, summaries):
    for call in d.calls:                          # guards: enclosing if-conditions testing a parameter
        if call is object_init_ex(target, ce): created[target] ∪= class_terms(ce)
        elif call is a Boundary Call: skip
        else for callee in resolve(call): created[call.args[i]] ∪= creates of callee at i, instantiated
    for call in d.calls:
        if call is a class throw primitive (ce, default): raise class_terms(ce, default)
        elif call is an object throw primitive (obj):     raise object_terms(obj)
        elif call is a Boundary Call:                     raise the classes its specifiers throw
        else for callee in resolve(call):
            for t in summaries[callee].raises: raise instantiate(t, call)
    returns = class_terms of each returned expression when d returns a class entry

instantiate(t, call):
    for (i, truth) in t.guards:
        a = call.args[i]
        if a is a literal: drop t when a's truth ≠ truth; else continue
        if a is a parameter p of the caller: guard (p, truth)
    drop t when its guards test one parameter both ways
    class_param(i, dflt) → class_terms(call.args[i], dflt); object_param(i) → object_terms(call.args[i])

class_terms(e, default):
    NULL → class(default); a parameter i → class_param(i, default);
    c ? x : y → both; Z_OBJCE(o) → class of object_terms(o); a local → its assignments;
    a registered class entry variable → class(its PHP name);
    a call → the returns of its callees, instantiated; else → open (unresolved)

object_terms(o):
    NULL → none; created in d → the created class terms; a parameter i → object_param(i); else → open
```

`resolve(call)` is the caller's own file first, else every header or
non-static definition of that name. A function name used as a value is a
call with unknown arguments, so a callback the body registers is entered.

### Edge Cases

- `zend_replace_error_handling(EH_THROW, ce, …)` throws `ce` for a later
  diagnostic; any other mode throws nothing.
- A Handler passing `NULL` to `zend_throw_error` throws `Error`; to
  `zend_throw_exception*`, `Exception`.
- `Z_PARAM_PATH` and the `p`/`P` format specifiers throw `ValueError` for a
  string holding a NUL byte; `Z_PARAM_CLASS` and `C` throw `TypeError` for
  a name that is no class. Every other binding throw is excluded.
- A guard tested with a literal at the call (`php_x(…, 1)` against
  `if (!throw_on_error)`) keeps or drops the term at that call.
- `assert` and `Generator::throw` throw the object their caller passes:
  the result is open, and the entry keeps no raises section.
- Every conditional-compilation branch is kept, so a class thrown under
  one configuration only (a debug build) is in the set.
- A value test the guard rule does not read (`if (ZEND_LONG_INT_OVFL(x))`)
  keeps the term: the set over-approximates.

### Invariants

- A summary only grows during the iteration of its component: every rule
  is monotone in the callee summaries.
- Callee components are final before their callers are evaluated.
- A Boundary Call is never entered; its specifier classes are its only
  contribution.
- Two runs over one checkout yield equal results.

### Termination

- Terms are drawn from finite sets: the classes and class entry variables
  of the checkout, the parameter indices, and the guard pairs of finitely
  many parameters. A component's summaries grow monotonically within
  that finite set, so each fixpoint iteration ends.

### Complexity

- Reading: O(S) over the source size S. Per component iteration: O(c · t)
  over its calls c and the terms t per callee summary. Iterations per
  component are bounded by the number of distinct guarded terms, O(T · 2^P)
  for the terms T and guard pairs P per summary; components are typically single
  definitions, so the run is close to linear in the call graph.
