# PHP Stubs — Extraction from php-src

## 1. Context

**Problem Statement**
The generated set states Facts about PHP builtins that only
the interpreter's own source decides: which class a builtin class extends,
which parameters a builtin function declares, and which exception classes
its implementation may throw. A stub-only declaration does not establish the exception classes thrown by its native implementation. php-src at the pinned release states all three: its stub files are the
declarations the interpreter's argument metadata is generated from, and its
C sources are the implementations.

**System Role**
The offline producers that rewrite the generated set from one
php-src release, beside the upstream stub conversion
([concept.md](concept.md), extraction tools).

**Data Flow**
- **Inputs:** one php-src checkout at the pinned release tag: its stub
  files, its function entry tables, and its C sources, including native
  object-handler declarations and implementations.
- **Outputs:** class hierarchies, final-class status, effective object-handler
  Facts, callable signatures, and throws sections
  of the generated entries; entries for every php-src declaration absent from the generated set.
- **Connections:** php-src → hierarchy extraction → signature extraction
  → throws extraction → `models/**` → the merge ([concept-lookup.md](concept-lookup.md)).

**Scope Boundaries**
- **Owned:** reading php-src, placing the entry of every php-src declaration in the document of its extension, rewriting its declaration
  fields and established effective object-handler Facts,
  signature, and throws of a generated entry.
- **Not Owned:** the format of a throws section and what it asserts
  ([commons-phpmodels model](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/model.md)); value units, which the value
  rules set states; the hand-declared `language/` and `manual/` documents.

## 2. Concepts

**Conceptual Diagram**
```
php-src (release tag)
  **/*.stub.php ─┐
  **/*.{c,h,cpp,cc} ┴─► Hierarchy Extraction ──► class declarations and handler facts
  **/*.stub.php ──────► Signature Extraction ──► function and method entries (params, returnType)
  *_arginfo.h  ───┐
  **/*.{c,h,cpp,cc}┴──► Throws Extraction ───► throws section of each implemented callable entry
                         (handlers → call graph → Procedure Summary per C function, boundaries cut)
```

**Core Concepts**

- **Name:** [Handler](glossary/glossary-extraction.md#handler).
- **Role:** Registered callable implementations provide roots for exception extraction.
- **Scope:** Ordinary and frameless implementations; abstract methods have none.
- **Relationships:** A Handler is a root of the Procedure Summary computation.

- **Name:** [Procedure Summary](glossary/glossary-extraction.md#procedure-summary).
- **Role:** Shared callee effects let extraction propagate throws through direct C calls.
- **Scope:** Reachable C functions and function-like macros in the throws analysis.
- **Relationships:** A caller instantiates callee effects at its argument expressions.

- **Name:** [Boundary Call](glossary/glossary-extraction.md#boundary-call).
- **Role:** Exclusions match the meaning of the dependency-owned throws Section.
- **Scope:** Argument binding, user-code calls, diagnostics and value conversion.
- **Relationships:** Boundary Calls restrict the call graph used for throws extraction.

## 3. Contracts & Flow

**Data Contracts**
- **With commons-phpmodels:** every written entry decodes under the
  format; a throws element is a class name the generated set declares.
- **With the merge:** a generated entry's throws section states the
  throws unit of that entry; a manual set states a correction as its
  own entry, never as an edit of a generated document.
- **With php-src:** one release tag per run; the same tag over the same
  documents yields identical files, and a second run changes nothing.

**Internal Processing Flow:** Upstream data becomes Document Sets, which the lookup loads for callers; the owning [procedure and software mapping](spec-throws.md) specifies this concern’s processing.

## 4. Scenarios

- **Typical:** `json_decode` gets `throws: [jsonexception, valueerror]`:
  its Handler throws `JsonException` when the flags argument requests it,
  and `ValueError` for a depth out of range.
- **Boundary:** `Generator::throw` rethrows the exception object its
  caller passes. No class set bounds it, so the entry keeps no throws
  section and asserts nothing.
- **Interaction:** `mysqli::query` receives its Signature and throws Section from php-src extraction and its reviewed Value unit from the manual rules set.

## 5. Rationale and Rejected Alternatives

- **Choice:** php-src stubs for hierarchies and signatures, so both use
  the interpreter's own declarations.
  **Rejected:** the upstream stub conversion (an older release, methods
  missing); PHP reflection as the producer (it reports only the extensions
  one build loads, so it serves as the test oracle instead).
- **Choice:** the throws section from a summary-based interprocedural
  analysis of the C sources, so the set is regenerated per release.
  **Rejected:** phpstorm-stubs `@throws` tags (hand-written, incomplete,
  spanning releases); the per-function throw extensions of static
  analyzers (a handful of builtins); dynamic testing (it observes throws
  but cannot state that a class is never thrown); hand-declared sections
  (several thousand entries no producer regenerates).
