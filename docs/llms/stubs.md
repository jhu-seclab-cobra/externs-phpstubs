# Stubs API

> PHP built-in declaration registry over commons-phpmodels entries.

## Quick Start

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs
import edu.jhu.cobra.externs.phpstubs.callableSignature

val func = PhpStubs.findFunction("strlen")               // StubEntry<FunctionSubject>?
val method = PhpStubs.findMethod("getMessage", "Exception")  // StubEntry<MethodSubject>?
val cls = PhpStubs.findClass("Exception")            // StubEntry<ClassSubject>?
func?.extension                                        // "standard"
func?.callableSignature?.returnType                    // DeclaredType("int")
```

## API

### PhpStubs (singleton)

**Existence checks:**

**`containsFunction(name: String): Boolean`** -- Includes keyword constructs (`echo`, `isset`, ...), extension `keyword`.

**`containsClass(name: String): Boolean`** -- Includes scalar types (`int`, `float`, ...; extension `scalar`), `exit` (`keyword`), and `resource` (`legacy`).

**`containsMethod(name: String, owner: String? = null): Boolean`** -- Qualified subject lookup when `owner` is given; suffix index on the folded method name when null.

**`containsConstant(name: String, caseSensitive: Boolean = true): Boolean`** -- Global constant, or class constant when spelled `Class::NAME`. `caseSensitive = false` reads the folded indexes.

**Entry retrieval:**

**`findFunction(name: String): StubEntry<FunctionSubject>?`**

**`findClass(name: String): StubEntry<ClassSubject>?`**

**`findMethod(name: String, owner: String? = null): StubEntry<MethodSubject>?`** -- First match in load order when `owner` is null. `entry.subject.owner` and `entry.subject.name` are folded.

**`findConstant(name: String, caseSensitive: Boolean = true): StubEntry<ConstantSubject>?`** -- Global constants only.

**`findClassConstant(name: String, owner: String? = null, caseSensitive: Boolean = true): StubEntry<ClassConstantSubject>?`** -- Suffix index when `owner` is null.

**Bulk access:**

**`functionNames: Set<String>`** -- Folded names, keyword constructs included.

**`classNames: Set<String>`** -- Folded names, scalar types and language classes included.

**`methodNames: Set<String>`** -- `owner::name` spellings, folded.

**`constantNames: Set<String>`** -- Global constants only, case preserved.

**`keywordFunctionNames: Set<String>`** -- Functions of the `keyword` extension: echo, empty, eval, exit, die, isset, print, unset, clone, instanceof, include, include_once, require, require_once.

**`scalarTypeNames: Set<String>`** -- Classes of the `scalar` extension: int, float, string, bool, array.

### StubEntry<S : ModelSubject> (data class)

**`subject: S`** -- The commons-phpmodels subject; equals `model.subject`.

**`model: SubjectModel`** -- The decoded entry: `signature`, `body` (propagation, returns, sources, sinks, sanitizers), `guard`.

**`extension: String`** -- Providing PHP extension, derived from the document file name (`standard_3.yaml` -> `standard`).

Typed accessors (top-level extension properties, non-null by the corpus rules):

**`StubEntry<FunctionSubject>.callableSignature`**, **`StubEntry<MethodSubject>.callableSignature`** -- `CallableSignature(params: List<ParameterInfo>, returnType: DeclaredType)`.

**`StubEntry<ClassSubject>.classSignature`** -- `ClassSignature(classifier, parent, interfaces)`; `parent` and `interfaces` are folded.

**`StubEntry<ConstantSubject>.typedSignature`**, **`StubEntry<ClassConstantSubject>.typedSignature`** -- `TypedSignature(type, value)`.

**`StubEntry<PropertySubject>.propertySignature`** -- `PropertySignature(type, visibility, static)`.

### StubRegistry (data class)

`functions`, `classes`, `methods`, `constants`, `classConstants`, `properties` -- unmodifiable maps from subject to entry.

### StubLoader (object)

**`loadAll(resourceBase: String = StubResources.MODELS): StubRegistry`** -- Loads the set through commons-phpmodels `DocumentSetLoader` over `StubResources.opener(resourceBase)`, attaches the extension per document path, enforces the corpus rules, freezes.

### StubResources (object)

**`MODELS: String`** -- `/models/`, the declaration set root.

**`TAINT: String`** -- `/taint/`, the taint set root: `vocabulary.yaml` (psalm's fifteen kinds, color `input`), `policy.yaml` (`input` enables the thirteen input kinds), `sinks.yaml`, `sanitizers.yaml`, `sources.yaml`.

**`TAINT_RULES: String`** -- `/taint-rules/`, the hand-maintained taint rules set root: `vocabulary.yaml` (adds kind `xpath`, color `external`), `policy.yaml` (`input` enables `xpath`; `external` enables the input kinds and `xpath`), `sinks.yaml`, `sanitizers.yaml`, `sources.yaml`. Decodes over the taint set's vocabulary; mounts after it.

**`opener(root: String): ResourceOpener`** -- Resolves `root + path` on this module's classpath; trailing slash optional; null for an absent path.

```kotlin
val psalm = DocumentSetLoader.load(StubResources.opener(StubResources.TAINT))
val mine = DocumentSetLoader.load(StubResources.opener(StubResources.TAINT), myVocabulary, myMapping)
val rules = DocumentSetLoader.load(StubResources.opener(StubResources.TAINT_RULES), psalm.vocabulary)
```

Taint entries carry no signature and exactly one of `sinks`, `sanitizers`, `sources`; `filter_var` appears as five guarded entries (`argument(1)` is 257, 258, 259, 519, 520) escaping `html`. Subjects are spelled as psalm names them (`mysqli::query`, `$_GET`). A taint rules entry for a subject the taint set also states restates psalm's points and adds its own (`readfile`: `file`, `unserialize`, plus `ssrf`, `html`).

### Exceptions

**`StubIndexNotFoundException`** -- `index.txt` or a listed document is absent from the classpath; the message names the full resource path.

**`StubIndexInvalidException`** -- The set loader rejects the set (malformed document, path listed twice, undeclared reference; cause attached, message names the document) or an entry violates a corpus rule: generator entry, variable subject, entry without signature, duplicate subject across documents.

**`IllegalArgumentException`** -- A facade lookup name is not a PHP identifier spelling.

## Gotchas

- Identity folding is decided by commons-phpmodels: `MethodSubject("Exception", "getMessage")` equals `MethodSubject("exception", "getmessage")`; `ConstantSubject("TRUE")` and `ConstantSubject("true")` differ.
- `containsMethod`/`findMethod` without `owner` and `findClassConstant` without `owner` return the first subject in load order; they are over-approximations.
- Language constructs are ordinary entries loaded from `models/language/`; select them by `extension`.
- Generated documents are never hand-edited; a correction belongs in a higher configuration layer of the consumer.
- Constant values are strings on `typedSignature.value`; the consumer converts.
- Taint rules are not registry entries; they are the `taint/` and `taint-rules/` document sets, mounted by the consumer through `DocumentSetLoader` with its own mapping, `taint-rules/` after `taint/`.
