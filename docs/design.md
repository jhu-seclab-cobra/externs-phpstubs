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

Data class. Fields: `name: String`, `type: PhpType`, `optional: Boolean` (default `false`), `defaultValue: String?` (default `null`). Invariant: non-optional param cannot have `defaultValue`. Enforced via `require` in `init`.

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

- `parse(reader: BufferedReader, extension: String): ParseResult` -- Parses one YAML file. Dispatches entries by `tag` field. Throws `StubIndexInvalidException` on unknown tags or missing required fields.
- `mapPhpType(typeStr: String): PhpType` -- Internal. Union types (containing `|`) resolve to `MIXED`. Unknown type names resolve to `MIXED`.
- `mapVisibility(raw: String?): Visibility` -- Internal. Null or unknown defaults to `PUBLIC`.

### `StubLoader` (object)

`loadAll(resourceBase: String = "/stubs/"): StubRegistry` -- Reads `index.txt` manifest from classpath, parses all listed YAML files, merges into a single `StubRegistry` with unmodifiable maps. Extension name derived from filename with `_\d+$` suffix stripped. Throws `StubIndexNotFoundException` if `index.txt` or any listed YAML file is missing.

### `PhpStubs` (object)

Facade. Lazy-loads `StubRegistry` on first access. Builds suffix indexes (method suffix after `::` mapped to full key) for O(1) lookup when `className` is null. `normalize()` strips leading `/` or `\` and lowercases.

Synthetic records: keyword functions (`echo`, `empty`, `eval`, `exit`, `die`, `isset`, `print`, `unset`, `clone`, `instanceof`, `shell_exec`, `include`, `include_once`, `require`, `require_once`) and synthetic classes (`int`, `float`, `string`, `bool`, `array`, `exit`, `resource`).

| Method | Return Type | Behavior |
|--------|-------------|----------|
| `containsFunc(name)` | `Boolean` | Checks registry and keyword set |
| `containsClass(name)` | `Boolean` | Checks registry and synthetic class records |
| `containsMethod(methodName, className?)` | `Boolean` | Full key if `className` provided; suffix index otherwise |
| `containsConst(name)` | `Boolean` | Checks global and class constants |
| `searchFunc(name)` | `Function?` | Keywords first, then registry |
| `searchClass(name)` | `PhpClass?` | Registry first, then synthetic |
| `searchMethod(methodName, className?)` | `Pair<String, Method>?` | Full key if `className` provided; suffix index otherwise |
| `searchGlobalConst(name)` | `Constant?` | Registry lookup |
| `searchClassConst(constName, className?)` | `ClassConstant?` | Full key if `className` provided; suffix index otherwise |
| `getAllFuncNames()` | `Set<String>` | Registry function keys |
| `getAllClassNames()` | `Set<String>` | Registry class keys |
| `getAllMethodNames()` | `Set<String>` | Registry method keys |
| `getAllConstNames()` | `Set<String>` | Registry constant keys |
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

- YAML files are UTF-8 encoded. Each file is a top-level YAML list of maps.
- Every entry requires a `tag` field. Unknown tags raise `StubIndexInvalidException`.
- Required fields per tag enforced at parse time by `YamlStubParser`.
- `flowsToReturn` values must be integers.
- Type strings containing `|` resolve to `MIXED`. Unknown type strings resolve to `MIXED`.
- Visibility strings are case-insensitive. Null or unknown defaults to `PUBLIC`.
- Duplicate names within the same entity type across files: last-loaded wins.
- All registry maps frozen as unmodifiable after loading.
- `index.txt` auto-generated by Gradle `processResources`. Lists relative paths of all `*.yaml` under `stubs/`, sorted alphabetically.
