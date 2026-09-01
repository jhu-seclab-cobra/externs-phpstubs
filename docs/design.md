# PHP Stubs — Design

Domain model and algorithm phases are skipped: the library is a registry
over types commons-phpmodels already defines (no domain semantics of its
own) and its load is a linear pass over documents (no worklist, fixpoint,
or traversal). Concepts: [concept.md](concept.md).

## Design Overview

- **Classes:** `StubEntry<S>` (data class), `StubRegistry` (data class),
  `StubLoader` (object), `PhpStubs` (object)
- **External types (commons-phpmodels):** `ModelLoader`, `ModelEntry`,
  `SubjectModel`, `ModelGenerator`, `ModelSubject` and its seven subtypes,
  `SignatureInfo` and its four subtypes, `ParameterInfo`, `DeclaredType`
- **Relationships:** `StubEntry` contains one `ModelSubject` subtype and one
  `SubjectModel`; `StubRegistry` contains `StubEntry` maps keyed by subject;
  `StubLoader` uses `ModelLoader` and builds `StubRegistry`; `PhpStubs`
  contains one `StubRegistry` and its lookup indexes. All arrows one-way.
- **Exceptions:** `StubIndexNotFoundException`, `StubIndexInvalidException`
  (both extend `RuntimeException`), raised by `StubLoader`.
- **Dependency roles:** Data holders: `StubEntry`, `StubRegistry`.
  Orchestrator: `StubLoader`. Facade: `PhpStubs`. Decoder and validator:
  commons-phpmodels.

Package `edu.jhu.cobra.externs.phpstubs`, one module, `explicitApi()`.
commons-phpmodels is an `api` dependency: its subject and signature types
are the entry surface. No YAML library is a direct dependency. Every type
in this file is public.

## Class / Type Specifications

### StubEntry<S : ModelSubject>

**Responsibility:** One registry entry: the decoded model together with its
extension provenance. Generic over the subject kind so a lookup result
exposes the identity fields of its kind (`owner`, `name`) without a cast.

**State/Fields:** `subject: S`, `model: SubjectModel`, `extension: String`
(the extension name derived from document placement; value tier: data,
never a constant in code).

**Validation (`init`):** `model.subject == subject`; `extension` non-blank.

**Typed signature accessors** (top-level extension properties in
`StubEntry.kt`, one per subject kind, narrowing `model.signature`):
`StubEntry<FunctionSubject>.callableSignature`,
`StubEntry<MethodSubject>.callableSignature`,
`StubEntry<ClassSubject>.classSignature`,
`StubEntry<ConstantSubject>.typedSignature`,
`StubEntry<ClassConstantSubject>.typedSignature`,
`StubEntry<PropertySubject>.propertySignature`. Non-null: the corpus rule
below requires a signature on every entry, and commons-phpmodels rejects a
signature subtype that does not match the subject kind.

### StubRegistry

**Responsibility:** The immutable per-kind entry maps, keyed by subject.

**State/Fields:** `functions: Map<FunctionSubject, StubEntry<FunctionSubject>>`,
`classes`, `methods`, `constants`, `classConstants`, `properties` — each
map keyed by its subject subtype. Every map is unmodifiable.

### StubLoader (object)

**Responsibility:** Builds one `StubRegistry` from the documents a manifest
lists. Owns the extension derivation and the corpus rules; owns no format
rule (commons-phpmodels decodes and validates every entry).

**Methods:**
- `loadAll(resourceBase: String = "/models/"): StubRegistry`
  - **Behavior:** reads `index.txt` under `resourceBase`; decodes each
    listed document through `ModelLoader.load`; attaches the extension
    derived from the document's file name (`.yaml` removed, then a trailing
    `_<digits>` split suffix removed); routes each entry into the map of
    its subject kind; freezes the maps.
  - **Input:** classpath directory holding `index.txt` and the documents it
    lists, trailing slash optional.
  - **Output:** the frozen registry.
  - **Errors:** `StubIndexNotFoundException` when `index.txt` or a listed
    document is absent (message names the resource path);
    `StubIndexInvalidException` on a decode failure (message names the
    document; cause is the commons-phpmodels `IllegalArgumentException`) or
    on a corpus rule violation.

**Corpus rules** (each violation is a `StubIndexInvalidException` naming
the document, and the subject where one exists):
- Every entry is a `SubjectModel`; a `ModelGenerator` is not stub data.
- No entry has a `VariableSubject`; predefined variables are not stubs.
- Every entry declares a `signature`.
- No two documents declare the same subject; the message names both.

Constant subjects fold nothing, so `TRUE` and `true` are distinct entries;
case-insensitive lookup over them is the facade's over-approximation.

### PhpStubs (object)

**Responsibility:** The lookup facade over one lazily loaded registry. Adds
the name-resolution rules of [concept.md](concept.md) Lookup Semantics:
unqualified member lookup through suffix indexes and case-insensitive
constant lookup through folded indexes. Every index is built once, lazily,
from the registry; every lookup afterwards is a map read.

**State (private, lazy):** the registry (`StubLoader.loadAll()`); the
method suffix index `name → MethodSubject`; the class-constant suffix
index `name → ClassConstantSubject` and its lowercased companion; the
folded constant index `lowercase name → ConstantSubject`; the folded
class-constant index `lowercase spelling → ClassConstantSubject`. Where
several subjects fold to one index key, the first in load order wins,
deterministically.

**Name handling:** a lookup name is converted to a subject through the
commons-phpmodels creators (`FunctionSubject.parse`, `ClassSubject.parse`,
`ConstantSubject.parse`; member constructors for a qualified lookup), so
folding and namespace-slash stripping are decided once, in the format
library. A name that is not a PHP identifier spelling (blank, whitespace,
`::`, `$`) is an argument error: `IllegalArgumentException` from the
creator, never a silent miss.

**Methods:**

| Method | Return | Behavior |
|--------|--------|----------|
| `containsFunc(name)` | `Boolean` | Function subject present (language constructs included) |
| `containsClass(name)` | `Boolean` | Class subject present (scalar types and `exit`, `resource` included) |
| `containsMethod(methodName, className?)` | `Boolean` | `searchMethod` non-null |
| `containsConst(name, caseSensitive = true)` | `Boolean` | Global or class constant present; folded indexes when `false` |
| `searchFunc(name)` | `StubEntry<FunctionSubject>?` | Registry read |
| `searchClass(name)` | `StubEntry<ClassSubject>?` | Registry read |
| `searchMethod(methodName, className?)` | `StubEntry<MethodSubject>?` | Qualified read when `className` given; suffix index otherwise |
| `searchGlobalConst(name, caseSensitive = true)` | `StubEntry<ConstantSubject>?` | Exact read, or folded index |
| `searchClassConst(constName, className?, caseSensitive = true)` | `StubEntry<ClassConstantSubject>?` | Qualified exact or folded read; suffix index (exact or folded) without `className` |
| `getAllFuncNames()` | `Set<String>` | Folded function names |
| `getAllClassNames()` | `Set<String>` | Folded class names |
| `getAllMethodNames()` | `Set<String>` | `owner::name` spellings, folded |
| `getAllConstNames()` | `Set<String>` | Global constant names, case preserved |
| `getKeywordFuncNames()` | `Set<String>` | Function names whose extension is `keyword` |
| `getScalarTypeNames()` | `Set<String>` | Class names whose extension is `scalar` |

`searchMethod` returns the entry alone: its subject carries the owner and
the folded name that the former key pair spelled. Language constructs are
ordinary entries, so the bulk name sets include them; the two derived sets
select by extension. Extension names `keyword` and `scalar` are constants
in `PhpStubs.kt` (fixed by the document layout).

## Resource Layout

```
models/
├── index.txt              # build-generated manifest, sorted relative paths
├── core.yaml              # extension "core"
├── language/              # hand-declared language constructs
│   ├── keyword.yaml       # 15 keyword functions + class exit, extension "keyword"
│   ├── scalar.yaml        # classes int, float, string, bool, array, extension "scalar"
│   └── legacy.yaml        # class resource, extension "legacy"
├── standard/standard_1..8.yaml   # extension "standard" (split suffix removed)
└── <category>/<extension>.yaml   # crypto, database, file, image, misc, network, system, text, xml
```

Generated documents carry the producer header of commons-phpmodels'
generated layer and are never hand-edited. The language documents are the
one hand-maintained exception and carry no producer header. A keyword
function declares one optional variadic `mixed` parameter and a `mixed`
return; a language class declares `classifier: class`.

The Gradle resource task writes `index.txt` for `models/` (main) and
`models-test/` (test); every other test fixture directory ships its own
manifest.

## Exception / Error Types

| Exception | When raised |
|-----------|-------------|
| `StubIndexNotFoundException(resource)` | `index.txt` or a listed document is not on the classpath |
| `StubIndexInvalidException(reason, cause?)` | A document fails commons-phpmodels decode (cause attached), or a corpus rule is violated |
| `IllegalArgumentException` | A facade lookup name is not a PHP identifier spelling (raised by the commons-phpmodels subject creator) |

## Validation Rules

- Format validation — YAML strictness, subject spellings, signature shape,
  arity, declared types — is commons-phpmodels' and is not repeated here.
- The four corpus rules above run in `StubLoader` at load, before any map
  is frozen; a violation fails the whole load.
- Duplicate detection compares subjects, so `Exception` and `exception`
  collide (folded kind) while `TRUE` and `true` do not (sensitive kind).
- `index.txt` lists relative document paths, one per line, sorted; blank
  lines and `#` comments are skipped.
