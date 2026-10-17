# PHP Stubs — Extraction Design

The offline producers that rewrite the generated set from
php-src. Concepts: [concept-extraction.md](concept-extraction.md). Throws
algorithm: [spec-throws.md](spec-throws.md). Resource layout and generated-set
rules: [design.md](design.md).

## Design Overview

- **Modules:** `tools/php_src.py` (shared reading, placement, and
  writing), `tools/extract_hierarchy.py`, `tools/extract_signatures.py`,
  `tools/extract_throws.py`; Python 3 standard library only. The test
  oracle `tools/reflect.php` runs on a PHP build, not over php-src.
- **Relationships:** each tool imports `php_src`; `php_src` imports no tool.
  The tools run in this order, because each reads what the earlier one
  wrote: a method joins its class's document, and a throws element names a
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
- **`document_extension(path)`** — the extension a document's placement
  encodes: its file name, split suffix removed (PHP Extension,
  [concept.md](concept.md)).
- **`placement(models, extension)`** — the document a new entry of an
  extension joins: the last generated document whose
  `document_extension` equals the extension
  (`standard` → `standard/standard_8.yaml`), else a new
  `models/<extension>.yaml` opened with the generated header naming the
  tool.
- **`relocate(models, extensions, tool)`** — moves each generated entry
  whose key `extensions` maps to an extension other than its document's
  to `placement` of that extension, its text unchanged; a document left
  without an entry is removed. Every php-src Declaration's entry thus
  lives in the document of the extension php-src declares it in.
- **`entries(text)`** — the entry spans of one document: from one
  `- subject:` line to the next; a rewrite replaces lines inside one span
  and leaves every other byte.

### extract_hierarchy.py

The class entries take their classifier, parent, and interfaces from
php-src, the interpreter's own declarations (CobraPHP user decision BP-2).

| Input | Yields |
|-------|--------|
| `**/*.stub.php` | each class, interface, enum, and trait with its namespace, `extends`, and `implements` names, folded |

- Each generated class entry php-src declares is relocated to its
  extension, then gets the classifier, parent, and interfaces php-src
  declares for its name; its other lines stay.
- An enum's interfaces end with `unitenum`, and with `unitenum`,
  `backedenum` when it declares a backing type: the interfaces the engine
  appends to every enum (`ENUM_INTERFACES`, `BACKED_ENUM_INTERFACES`,
  constant tier, read off `zend_enum_add_interfaces` in `Zend/zend_enum.c`).
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
- Each generated function or method entry php-src declares is relocated
  to its extension, then gets the subject line and signature block
  php-src states; its other sections (propagation, throws) stay, except a
  propagation statement naming an argument position the signature lacks
  (no variadic parameter): PHP rejects a call passing more arguments
  than an internal function declares (`ArgumentCountError`), so no value
  reaches that position. A propagation section left without a statement
  fails the run.
- A php-src function no models document declares joins `placement` of its
  extension; a method joins the generated document declaring its class,
  and a class no generated document declares fails the run.

### extract_throws.py

| Input | Yields |
|-------|--------|
| `**/*_arginfo.h` function entry tables (`ZEND_FE`, `ZEND_ME`, `ZEND_RAW_FENTRY`, the frameless tables) and class registrations | each registered function and method with its Handlers |
| `**/*.{c,h,cpp,cc}` | C function definitions, handler macro definitions, and function-like macros, conditional-compilation branches kept |

- **Output:** each generated function or method entry with at least one
  Handler gets the line `  throws: [<classes>]` as its last line, the
  classes folded and sorted, `[]` for none. An entry whose Handlers throw
  an object the caller supplies gets no line and is printed. Every other
  generated callable entry keeps no `throws` line: this tool owns the
  line in generated documents. A method table no class registration
  names is printed and keys no entry.
- **Tables (constant tier, each naming the php-src header it reads):**
  the handler-defining macros, the throwing primitives and their class or
  object argument, the object creation primitive, the binding prefixes and
  the specifiers that throw beyond the declared type, the user-code
  entries, the diagnostic prefixes, and the conversion prefixes of
  `Zend/zend_operators.h`.
- **Fails** when a class expression no rule resolves reaches an entry,
  when a throws element names a class no generated document declares,
  when a Handler has no definition, or when a source brace is unbalanced.

### reflect.php

The test oracle of the generated set: `php tools/reflect.php` on a PHP
8.5.11 build writes `src/test/resources/reflection/php_8_5_11.tsv`, one
sorted tab-separated line per internal declaration the build reflects.

| Line | Fields |
|------|--------|
| `function` | folded name, return type, parameters |
| `method` | folded `class::name` of each method the class itself declares, return type, parameters |
| `class` | folded name, folded parent or `-`, every interface folded, sorted, comma-joined, or `-` |

- A parameter is `<name> <type> <flags>`, the flags drawn from `o`
  (optional), `r` (by reference), `v` (variadic), `-` for none. An
  omitted type is `mixed`; a return type falls back to the tentative one.
- `ReflectionOracleTest` reads the fixture and checks the bundled set:
  every reflected callable is found by function lookup or by method
  lookup over the class, its parents, and its interfaces; every declared
  signature admits the reflected one (the rule a kept variant obeys,
  `iterable` read as `Traversable|array` as PHP compiles it); every
  reflected class carries the reflected parent and transitive interfaces.

## Exception / Error Types

| Failure | When |
|---------|------|
| Unreadable declaration | A stub header, parameter, or return type no rule reads |
| Conflicting declarations | Two stubs, or two variants, declare one subject and neither subsumes the other |
| Undeclared class | A method's class or a throws element is declared by no generated document |
| Unresolved class | A class expression no rule resolves reaches an entry's throws |
| Unknown entry macro | A function entry table uses a macro outside the known set |
| Undefined Handler | An entry names a Handler no C source defines |
| Unbalanced source | A C source holds a brace no brace closes |
| Propagation without a port | Every propagation statement of an entry names an argument position its php-src signature lacks |

## Open Gaps

- **Indirect calls.** The model asserts that a class outside an entry's
  throws section is never thrown by it (commons-phpmodels `docs/model.md`,
  Relations). `extract_throws.py` follows calls by name only; a call
  through a struct member or a function pointer (object handler tables,
  class entry hooks such as `get_iterator`, stream wrapper operations,
  C++ member calls) is not followed, so a class only such a call throws is
  missing. Example: `iterator_to_array` over a finished generator throws
  `Exception` ("Cannot traverse an already closed generator") through
  `zend_generator_get_iterator`, and its section names `error` and
  `typeerror` only. Candidate: resolve such a call to every function
  stored into a field of the same struct type (multi-layer type analysis).
- **`Closure::__invoke`.** The engine attaches it to every closure object
  at call time; no stub declares it, so no entry exists and the oracle
  test lists it as the one undeclared reflected callable.
- **PDO driver methods.** php-src declares `PDO_PGSql_Ext` and
  `PDO_SQLite_Ext` as stub-only pseudo classes whose methods PHP attaches
  to a `PDO` object of that driver; no class registration names their
  method tables, so their entries keep no `throws` line and
  `extract_throws.py` prints the two tables.
