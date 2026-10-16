# PHP Stubs — Extraction Design

The offline producers that rewrite the generated declaration set from
php-src. Concepts: [concept-extraction.md](concept-extraction.md). Raises
algorithm: [spec-raises.md](spec-raises.md). Resource layout and corpus
rules: [design.md](design.md).

## Design Overview

- **Modules:** `tools/php_src.py` (shared reading, placement, and
  writing), `tools/extract_hierarchy.py`, `tools/extract_signatures.py`,
  `tools/extract_raises.py`; Python 3 standard library only.
- **Relationships:** each tool imports `php_src`; `php_src` imports no tool.
  The tools run in this order, because each reads what the earlier one
  wrote: a method joins its class's document, and a raises element names a
  declared class.
- **Errors:** a tool prints `<tool>: <reason>` naming the php-src file or
  the subject, exits with status 1, and leaves the documents as the last
  completed write left them.
- **Dependency roles:** Readers and writers: `php_src`. One orchestrating
  `main` per tool.

Every tool takes `--php-src <root>` (a checkout at tag `php-8.5.11`) and
`--models <models dir>`, writes the generated documents under `models/` in
place, and never writes `language/`, `manual/`, or `provenance.yaml`.
Output is deterministic, and a second run over its own output changes
nothing.

## Function Specifications

### php_src (module)

- **`source_files(root, suffixes)`** — every file of the checkout with
  one of the suffixes, sorted, skipping any path with a part in
  `SKIPPED_SOURCE_PARTS` (`tests`, `zend_test`, `dl_test`, `skeleton`).
- **`resolve(name, namespace, imports)`** — PHP name resolution:
  fully qualified, imported, or relative to the namespace; the spelling is
  kept, and the caller folds where a subject is meant.
- **`extension_of(source)`** — `ext/<dir>/…` → `<dir>`; `Zend/` → `core`;
  `main/`, `sapi/` → `standard` (`EXTENSION_OF_DIRECTORY`, constant tier,
  read off PHP reflection's extension of those declarations).
- **`generated_documents(models)`** — every document except the
  `HAND_DECLARED` directories (`language`, `manual`) and `provenance.yaml`.
- **`placement(models, extension)`** — the document a new entry of an
  extension joins: the last generated document whose name, split suffix
  removed, equals the extension (`standard` → `standard/standard_8.yaml`),
  else a new `models/<extension>.yaml` opened with the generated header
  naming the tool.
- **`entries(text)`** — the entry spans of one document: from one
  `- subject:` line to the next; a rewrite replaces lines inside one span
  and leaves every other byte.

### extract_hierarchy.py

The class entries take their classifier, parent, and interfaces from
php-src, the interpreter's own declarations (CobraPHP user decision BP-2).

| Input | Yields |
|-------|--------|
| `**/*.stub.php` | each class, interface, enum, and trait with its namespace, `extends`, and `implements` names, folded |

- Each generated class entry gets the classifier, parent, and interfaces
  php-src declares for its name; its other lines stay.
- Each php-src class-like declaration no models document declares is
  added to `placement` of its extension.
- A class php-src does not declare (a PECL class) keeps its entry.
- Two stubs declaring one class with different hierarchies fail.

### extract_signatures.py

| Input | Yields |
|-------|--------|
| `**/*.stub.php` | each function and method: parameter names, declared types, by-reference, variadic, and default marks, the return type |

- A parameter is `optional` when it declares a default or is variadic, and
  `byRef` when declared `&` or tagged `@prefer-ref` in its doc comment
  (the interpreter passes such an argument by reference when it can).
- A type php-src omits is `mixed`, PHP's reading of an omitted type. A
  class name in a type is resolved and keeps its spelling.
- A declaration stated in several conditional-compilation variants keeps
  the variant that subsumes the other: it admits every call the other
  admits and its return type includes the other's. Neither subsuming
  fails the run.
- Each generated function or method entry php-src declares gets the
  subject line and signature block php-src states; its other sections
  (propagation, raises) stay.
- A php-src function no models document declares joins `placement` of its
  extension; a method joins the generated document declaring its class,
  and a class no generated document declares fails the run.

### extract_raises.py

| Input | Yields |
|-------|--------|
| `**/*_arginfo.h` function entry tables (`ZEND_FE`, `ZEND_ME`, `ZEND_RAW_FENTRY`, the frameless tables) and class registrations | each registered function and method with its Handlers |
| `**/*.{c,h,cpp,cc}` | C function definitions, handler macro definitions, and function-like macros, conditional-compilation branches kept |

- **Output:** each generated function or method entry with at least one
  Handler gets the line `  raises: [<classes>]` as its last line, the
  classes folded and sorted, `[]` for none. An entry whose Handlers throw
  an object the caller supplies gets no line and is printed. Every other
  generated callable entry keeps no `raises` line: this tool owns the
  line in generated documents.
- **Tables (constant tier, each naming the php-src header it reads):**
  the handler-defining macros, the throwing primitives and their class or
  object argument, the object creation primitive, the binding prefixes and
  the specifiers that throw beyond the declared type, the user-code
  entries, the diagnostic prefixes, and the conversion prefixes of
  `Zend/zend_operators.h`.
- **Fails** when a class expression no rule resolves reaches an entry, or
  when a raises element names a class no generated document declares.

## Exception / Error Types

| Failure | When |
|---------|------|
| Unreadable declaration | A stub header, parameter, or return type no rule reads |
| Conflicting declarations | Two stubs, or two variants, declare one subject and neither subsumes the other |
| Undeclared class | A method's class or a raises element is declared by no generated document |
| Unresolved class | A class expression no rule resolves reaches an entry's raises |
| Unknown entry macro | A function entry table uses a macro outside the known set |

## Open Gaps

- **Indirect calls.** The model asserts that a class outside an entry's
  raises section is never thrown by it (commons-phpmodels `docs/model.md`,
  Relations). `extract_raises.py` follows calls by name only; a call
  through a struct member or a function pointer (object handler tables,
  class entry hooks such as `get_iterator`, stream wrapper operations,
  C++ member calls) is not followed, so a class only such a call throws is
  missing. Example: `iterator_to_array` over a finished generator throws
  `Exception` ("Cannot traverse an already closed generator") through
  `zend_generator_get_iterator`, and its section names `error` and
  `typeerror` only. Candidate: resolve such a call to every function
  stored into a field of the same struct type (multi-layer type analysis).
