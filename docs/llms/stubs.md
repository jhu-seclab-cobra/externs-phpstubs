# Stubs API

> PHP built-in declaration registry over commons-phpmodels entries.

## Quick Start

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs
import edu.jhu.cobra.externs.phpstubs.callableSignature

val func = PhpStubs.searchFunc("strlen")               // StubEntry<FunctionSubject>?
val method = PhpStubs.searchMethod("getMessage", "Exception")  // StubEntry<MethodSubject>?
val cls = PhpStubs.searchClass("Exception")            // StubEntry<ClassSubject>?
func?.extension                                        // "standard"
func?.callableSignature?.returnType                    // DeclaredType("int")
```

## API

### PhpStubs (singleton)

**Existence checks:**

**`containsFunc(name: String): Boolean`** -- Includes keyword constructs (`echo`, `isset`, ...), extension `keyword`.

**`containsClass(name: String): Boolean`** -- Includes scalar types (`int`, `float`, ...; extension `scalar`), `exit` (`keyword`), and `resource` (`legacy`).

**`containsMethod(methodName: String, className: String? = null): Boolean`** -- Qualified subject lookup when `className` is given; suffix index on the folded method name when null.

**`containsConst(name: String, caseSensitive: Boolean = true): Boolean`** -- Global constant, or class constant when spelled `Class::NAME`. `caseSensitive = false` reads the folded indexes.

**Entry retrieval:**

**`searchFunc(name: String): StubEntry<FunctionSubject>?`**

**`searchClass(name: String): StubEntry<ClassSubject>?`**

**`searchMethod(methodName: String, className: String? = null): StubEntry<MethodSubject>?`** -- First match in load order when `className` is null. `entry.subject.owner` and `entry.subject.name` are folded.

**`searchGlobalConst(name: String, caseSensitive: Boolean = true): StubEntry<ConstantSubject>?`** -- Global constants only.

**`searchClassConst(constName: String, className: String? = null, caseSensitive: Boolean = true): StubEntry<ClassConstantSubject>?`** -- Suffix index when `className` is null.

**Bulk access:**

**`getAllFuncNames(): Set<String>`** -- Folded names, keyword constructs included.

**`getAllClassNames(): Set<String>`** -- Folded names, scalar types and language classes included.

**`getAllMethodNames(): Set<String>`** -- `owner::name` spellings, folded.

**`getAllConstNames(): Set<String>`** -- Global constants only, case preserved.

**`getKeywordFuncNames(): Set<String>`** -- Functions of the `keyword` extension: echo, empty, eval, exit, die, isset, print, unset, clone, instanceof, include, include_once, require, require_once.

**`getScalarTypeNames(): Set<String>`** -- Classes of the `scalar` extension: int, float, string, bool, array.

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

**`loadAll(resourceBase: String = "/models/"): StubRegistry`** -- Reads `index.txt`, decodes each listed document with `ModelLoader`, attaches the extension, enforces the corpus rules, freezes.

### Exceptions

**`StubIndexNotFoundException`** -- `index.txt` or a listed document is absent from the classpath.

**`StubIndexInvalidException`** -- A document fails commons-phpmodels decode (cause attached, message names the document) or violates a corpus rule: generator entry, variable subject, entry without signature, duplicate subject across documents.

**`IllegalArgumentException`** -- A facade lookup name is not a PHP identifier spelling.

## Gotchas

- Identity folding is decided by commons-phpmodels: `MethodSubject("Exception", "getMessage")` equals `MethodSubject("exception", "getmessage")`; `ConstantSubject("TRUE")` and `ConstantSubject("true")` differ.
- `containsMethod`/`searchMethod` without `className` and `searchClassConst` without `className` return the first subject in load order; they are over-approximations.
- Language constructs are ordinary entries loaded from `models/language/`; select them by `extension`.
- Generated documents are never hand-edited; a correction belongs in a higher configuration layer of the consumer.
- Constant values are strings on `typedSignature.value`; the consumer converts.
- Taint rules (source/sink/sanitizer) are NOT in this library.
