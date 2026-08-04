# PHP Stubs Library Design

## Design Overview

- **Sealed class**: `StubRecord` (6 subtypes: `Function`, `Method`, `PhpClass`, `Constant`, `ClassConstant`, `Property`)
- **Data classes**: `StubParam`, `StubRegistry`, `YamlStubParser.ParseResult`
- **Enums**: `PhpType`, `Visibility`
- **Objects**: `YamlStubParser`, `StubLoader`, `PhpStubs`
- **Relationships**: `StubLoader` reads YAML via `YamlStubParser`, builds `StubRegistry`. `PhpStubs` delegates to `StubRegistry`.
- **Exceptions**: `StubIndexNotFoundException`, `StubIndexInvalidException` (both extend `RuntimeException`)
- **Dependency roles**: Data holders: `StubRecord`, `StubParam`, `StubRegistry`, `ParseResult`. Orchestrator: `StubLoader`. Parser: `YamlStubParser`. Facade: `PhpStubs`.

---

## YAML Format

### Tag System

Each YAML file contains a flat list of map entries. Every entry has a `tag` field.

| Tag | Description | Example |
|-----|-------------|---------|
| `function` | Top-level PHP function | `strlen`, `array_map` |
| `method` | Class method | `PDO::prepare` |
| `class` | Class or interface definition | `Exception`, `PDOStatement` |
| `constant` | Global constant | `PHP_INT_MAX`, `ENT_QUOTES` |
| `class_constant` | Class constant | `PDO::ATTR_ERRMODE` |
| `property` | Class property | `Exception::$message` |

### Entry Schemas

**`function`**: `tag` (required), `name` (required), `params` (list, optional), `return` (string, default `mixed`), `flowsToReturn` (list[int], optional -- parameter indices whose data flows to return value).

**`params` element**: `name` (required), `type` (string, default `mixed`), `optional` (bool, default `false`), `default` (string, optional -- default value literal).

**`method`**: `tag` (required), `class` (required -- owning class), `name` (required), `params` (same as `function`), `return` (default `mixed`), `static` (bool, default `false`), `visibility` (`public`/`protected`/`private`, default `public`), `flowsToReturn` (list[int], optional -- 0 = first explicit parameter).

**`class`**: `tag` (required), `name` (required), `parent` (string, optional), `interfaces` (list[string], optional), `abstract` (bool, default `false`), `final` (bool, default `false`).

**`constant`**: `tag` (required), `name` (required), `type` (required), `value` (required).

**`class_constant`**: `tag` (required), `class` (required), `name` (required), `type` (required), `value` (required), `visibility` (default `public`).

**`property`**: `tag` (required), `class` (required), `name` (required), `type` (default `mixed`), `static` (bool, default `false`), `visibility` (default `public`).

### File Organization

```
stubs/
├── core.yaml              # core constructs, Exception hierarchy, constants
├── crypto/                # bcmath, gmp, hash, mcrypt, openssl
├── database/              # cubrid, dba, ibm_db2, mysqli, oci8, odbc, pgsql
├── file/                  # bz2, exif, file, fileinfo, filter, zip, zlib
├── image/                 # gd
├── misc/                  # apcu, date, yp
├── network/               # curl, ftp, imap, ldap, session, sockets, stream
├── standard/              # standard_1..standard_8 (split for size)
├── system/                # pcntl, posix, readline, spl, sysvmsg, sysvsem, sysvshm
├── text/                  # ctype, gettext, iconv, intl, json, mbstring, pcre
├── xml/                   # libxml, simplexml, tidy, xml, xmlwriter
└── index.txt              # auto-generated manifest (Gradle processResources)
```

### Data Extraction Pipeline

YAML stub files are produced offline by a script that parses JetBrains PhpStorm PHP stubs (`.phpstub` source files) and emits the unified YAML format. The script is not part of this library. The resulting YAML files are committed as resources and shipped in the JAR.

---

## Class / Type Specifications

### `PhpType`

Enum. Values: `STRING`, `INT`, `FLOAT`, `BOOL`, `ARRAY`, `OBJECT`, `MIXED`, `VOID`, `NULL`, `CALLABLE`, `RESOURCE`.

### `Visibility`

Enum. Values: `PUBLIC`, `PROTECTED`, `PRIVATE`.

### `StubParam`

Data class. Fields: `name: String`, `type: PhpType`, `optional: Boolean` (default `false`), `defaultValue: String?` (default `null`). Invariant: non-optional param cannot have `defaultValue`. `YamlStubParser` validates the combination at parse time and raises `StubIndexInvalidException` naming the source file and param; the `require` in `init` remains as a backstop for direct construction.

### `StubRecord` (sealed class)

Base properties: `name: String`, `extension: String`.

| Subtype | Fields (beyond base) |
|---------|---------------------|
| `Function` | `params: List<StubParam>`, `returnType: PhpType`, `flowsToReturn: Set<Int>` |
| `Method` | `owningClass: String`, `params: List<StubParam>`, `returnType: PhpType`, `flowsToReturn: Set<Int>`, `visibility: Visibility`, `isStatic: Boolean` |
| `PhpClass` | `parent: String?`, `interfaces: List<String>`, `isAbstract: Boolean`, `isFinal: Boolean` |
| `Constant` | `type: PhpType`, `value: String` |
| `ClassConstant` | `owningClass: String`, `type: PhpType`, `value: String`, `visibility: Visibility` |
| `Property` | `owningClass: String`, `type: PhpType`, `visibility: Visibility`, `isStatic: Boolean` |

### `StubRegistry`

Data class. Six typed unmodifiable maps:
`functions: Map<String, StubRecord.Function>`, `classes: Map<String, StubRecord.PhpClass>`, `methods: Map<String, StubRecord.Method>`, `constants: Map<String, StubRecord.Constant>`, `classConstants: Map<String, StubRecord.ClassConstant>`, `properties: Map<String, StubRecord.Property>`.

### `YamlStubParser` (object)

**`ParseResult`**: nested data class with six typed lists matching `StubRegistry` field types.

- `parse(reader: BufferedReader, source: String, extension: String): ParseResult` -- Parses one YAML file. Dispatches entries by `tag` field. Throws `StubIndexInvalidException` on unknown tags or missing required fields; every error message is prefixed with `source`.
- `mapPhpType(typeStr: String, source: String): PhpType` -- Internal. Union types (containing `|`) resolve to `MIXED`. Unknown type names raise `StubIndexInvalidException`.
- `mapVisibility(raw: String?, source: String): Visibility` -- Internal. Null (absent field) defaults to `PUBLIC`; unknown values raise `StubIndexInvalidException`.

### `StubLoader` (object)

`loadAll(resourceBase: String = "/stubs/"): StubRegistry` -- Reads `index.txt` manifest from classpath, parses all listed YAML files, merges into a single `StubRegistry` with unmodifiable maps. Extension name derived from filename with `_\d+$` suffix stripped. Throws `StubIndexNotFoundException` if `index.txt` or any listed YAML file is missing; the message names the missing resource path.

Key normalization follows PHP case sensitivity: function, class, method, and property keys are lowercased. Constant keys (global and class) strip one leading `/` or `\` namespace separator and preserve original case from YAML. Class-constant keys use lowercased class name + original constant name (`exception::SEVERITY_ERROR`). Qualified member keys are built by the shared `qualifiedStubKey()` in `StubKey.kt`, used by both `StubLoader` and `PhpStubs`.

### `PhpStubs` (object)

Facade. Lazy-loads `StubRegistry` on first access. Builds suffix indexes (method suffix after `::` mapped to full key) for O(1) lookup when `className` is null. Method suffixes are lowercased by key normalization; the class-constant suffix index is case-preserved, with a lazy lowercased companion index serving case-insensitive suffix lookups.

**Case sensitivity follows PHP semantics:**
- Functions, classes, methods: case-insensitive. `normalizeStubKey()` (shared with `StubLoader`) strips leading `/` or `\` and lowercases.
- Constants (global and class): **case-sensitive by default** (`PHP_INT_MAX` ≠ `php_int_max`). Constant-related methods accept `caseSensitive: Boolean = true`. Pass `false` for over-approximation in static analysis.

Synthetic records: keyword functions (`echo`, `empty`, `eval`, `exit`, `die`, `isset`, `print`, `unset`, `clone`, `instanceof`, `shell_exec`, `include`, `include_once`, `require`, `require_once`) and synthetic classes (`int`, `float`, `string`, `bool`, `array`, `exit`, `resource`).

| Method | Return Type | Behavior |
|--------|-------------|----------|
| `containsFunc(name)` | `Boolean` | Checks registry and keyword set (case-insensitive) |
| `containsClass(name)` | `Boolean` | Checks registry and synthetic class records (case-insensitive) |
| `containsMethod(methodName, className?)` | `Boolean` | Full key if `className` provided; suffix index otherwise (case-insensitive) |
| `containsConst(name, caseSensitive?)` | `Boolean` | Checks global and class constants. Default case-sensitive |
| `searchFunc(name)` | `Function?` | Keywords first, then registry (case-insensitive) |
| `searchClass(name)` | `PhpClass?` | Registry first, then synthetic (case-insensitive) |
| `searchMethod(methodName, className?)` | `Pair<String, Method>?` | Full key if `className` provided; suffix index otherwise (case-insensitive) |
| `searchGlobalConst(name, caseSensitive?)` | `Constant?` | Registry lookup. Default case-sensitive |
| `searchClassConst(constName, className?, caseSensitive?)` | `ClassConstant?` | Class name case-insensitive, constant name case-sensitive by default. With `caseSensitive = false` and no `className`, the lowercased suffix index matches uppercase constants from any-case input |
| `getAllFuncNames()` | `Set<String>` | Registry function keys (lowercase) |
| `getAllClassNames()` | `Set<String>` | Registry class keys (lowercase) |
| `getAllMethodNames()` | `Set<String>` | Registry method keys (lowercase class::lowercase method) |
| `getAllConstNames()` | `Set<String>` | Registry constant keys (original case) |
| `getKeywordFuncNames()` | `Set<String>` | Hardcoded keyword set |
| `getScalarTypeNames()` | `Set<String>` | Hardcoded scalar type set |

---

## Exception / Error Types

| Exception | When Raised |
|-----------|-------------|
| `StubIndexNotFoundException` | YAML resource or `index.txt` not found on classpath |
| `StubIndexInvalidException` | Missing required field, unknown tag, or invalid field value in YAML |

---

## Validation Rules

- YAML files are UTF-8 encoded. Each file is a top-level YAML list of maps. Files are loaded with SnakeYAML's `SafeConstructor` (standard types only, no arbitrary object instantiation).
- Syntactically malformed YAML raises `StubIndexInvalidException` naming the source file, with the SnakeYAML error as cause.
- Every entry requires a `tag` field. Unknown tags raise `StubIndexInvalidException`.
- Required fields per tag enforced at parse time by `YamlStubParser`.
- Boolean fields (`static`, `abstract`, `final`, `optional`) must be YAML booleans; present non-boolean values (e.g. the string `"true"`) raise `StubIndexInvalidException` naming the field.
- A param with `optional: false` and a `default` raises `StubIndexInvalidException` naming the param.
- `flowsToReturn` values must be integers.
- Type strings containing `|` resolve to `MIXED`. Unknown type strings raise `StubIndexInvalidException`.
- Visibility strings are case-insensitive. Absent visibility defaults to `PUBLIC`; unknown values raise `StubIndexInvalidException`.
- Duplicate keys within the same entity type raise `StubIndexInvalidException` naming the key and both defining files.
- All registry maps frozen as unmodifiable after loading.
- `index.txt` auto-generated by Gradle `processResources`. Lists relative paths of all `*.yaml` under `stubs/`, sorted alphabetically.
