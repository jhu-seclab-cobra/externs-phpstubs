# PHP Stubs — Extraction from php-src

## 1. Context

**Problem Statement**
The generated set states facts about PHP builtins that only
the interpreter's own source decides: which class a builtin class extends,
which parameters a builtin function declares, and which exception classes
its implementation may throw. The upstream stub conversion that seeded the
set covers an older release, omits most methods, and states no throw at
all. php-src at the pinned release states all three: its stub files are the
declarations the interpreter's argument metadata is generated from, and its
C sources are the implementations.

**System Role**
The offline producers that rewrite the generated set from one
php-src release, beside the upstream stub conversion
([concept.md](concept.md), Extraction Pipeline).

**Data Flow**
- **Inputs:** one php-src checkout at the pinned release tag: its stub
  files, its function entry tables, and its C sources, including native
  object-handler declarations and implementations.
- **Outputs:** class hierarchies, final-class status, effective object-handler
  facts, callable signatures, and throws sections
  of the generated entries; entries for every php-src declaration the set
  lacked.
- **Connections:** php-src → hierarchy extraction → signature extraction
  → throws extraction → `models/**` → the merge ([concept-lookup.md](concept-lookup.md)).

**Scope Boundaries**
- **Owned:** reading php-src, placing the entry of every php-src
  Declaration in the document of its extension, rewriting its declaration
  fields and established effective object-handler facts,
  signature, and throws of a generated entry.
- **Not Owned:** the format of a throws section and what it asserts
  (commons-phpmodels `docs/model.md`); value units, which the value
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

- **Name:** php-src Declaration
- **Definition:** One class-like, function, or method declaration of a
  php-src stub file, with names resolved by PHP's name resolution rules.
  The stub is the declaration the interpreter registers: its argument
  metadata is generated from it, so it agrees with reflection by
  construction.
- **Scope:** every stub outside test directories and the extension
  skeleton.
- **Relationships:** read by the Hierarchy and Signature Extractions;
  placed by its PHP Extension ([concept.md](concept.md)).

- **Name:** Handler
- **Definition:** The C function the interpreter calls for one builtin,
  named by the builtin's function entry table; a builtin with a
  specialized form (frameless call) has one Handler per form.
- **Scope:** every function and method entry php-src registers; an
  abstract method has none.
- **Relationships:** the roots of the Throws Extraction.

- **Name:** Procedure Summary
- **Definition:** What one C function may contribute to a builtin's
  throws section: the exception classes it may throw, each with the
  parameter tests it is guarded by, plus the classes it creates into a
  parameter and the class entries it returns, so a caller resolves a class
  passed down to it.
- **Scope:** every C function and function-like macro reachable from a
  Handler; computed by [spec-throws.md](spec-throws.md).
- **Relationships:** a Handler's throws section is the union of the
  classes its Procedure Summary names.

- **Name:** Boundary Call
- **Definition:** A call whose exceptions the throws section excludes by the
  format's definition: argument binding, a call into user code, a
  diagnostic, and a value conversion. The analysis does not enter it; a
  binding specifier that checks a value beyond its declared type still
  contributes the class it throws.
- **Relationships:** cuts the call graph the Procedure Summary is computed
  over.

## 3. Contracts & Flow

**Data Contracts**
- **With commons-phpmodels:** every written entry decodes under the
  format; a throws element is a class name the generated set declares.
- **With the merge:** a generated entry's throws section states the
  throws unit of that entry; a manual set states a correction as its
  own entry, never as an edit of a generated document.
- **With php-src:** one release tag per run; the same tag over the same
  documents yields identical files, and a second run changes nothing.

**Internal Processing Flow**
1. Hierarchy — every php-src class-like declaration gets its declaration
   fields and established handler facts; one the set lacks is added.
2. Signatures — every php-src function and method gets its declared
   parameters and return type; one the set lacks is added.
3. Throws — every implemented function and method gets the classes its
   Handlers may throw, or no throws section when a Handler throws an
   object the caller supplies.

## 4. Scenarios

- **Typical:** `json_decode` gets `throws: [jsonexception, valueerror]`:
  its Handler throws `JsonException` when the flags argument requests it,
  and `ValueError` for a depth out of range.
- **Boundary:** `Generator::throw` rethrows the exception object its
  caller passes. No class set bounds it, so the entry keeps no throws
  section and asserts nothing.
- **Interaction:** `mysqli::query` was a hand-declared manual method. Once
  the Signature Extraction adds it from php-src, the manual entry would
  duplicate a generated subject, so its reviewed flow moves to the value
  rules set ([concept-value-rules.md](concept-value-rules.md)) and the
  generated entry carries the signature and the throws section.

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
