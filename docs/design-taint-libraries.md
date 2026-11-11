# Library Taint Sets — Design

Concepts: [concept-taint-libraries.md](concept-taint-libraries.md). Mounting and precedence: [design-merge.md](design-merge.md).

## Design Overview

- **Classes:** `LibrarySet`, `PhpStubs`, `MountSequence`.
- **Relationships:** `PhpStubs` reads the catalog and extends its mounts through `MountSequence`; the importer produces the catalog and package roots.
- **Abstract:** No additional lookup interface.
- **Exceptions:** `IllegalArgumentException`, `StubIndexNotFoundException`, `StubIndexInvalidException`.
- **Dependency roles:** Metadata: `LibrarySet`. Selection: `PhpStubs`. Decoding: the safe YAML reader and the existing Document Set loader. Offline production: `tools/import_library.py`.

Signatures come from declarations [@psalm-plugin-laravel; @psalm-plugin-doctrine; @psalm7]. Additional endpoint lists [@phpstan-security; @codeql-php] contribute only when a declaration resolves.

## Class / Type Specifications

### LibrarySet

A catalog row contains `package` (exact Composer name), `version` (the version or constraint the stubs describe, or `unknown`), `upstreams` (source names with release identities), and `root` (classpath directory). A major line or constraint is not an exact installed release.

### PhpStubs

`libraries: List<LibrarySet>` reads the machine-readable catalog lazily. Duplicate package names, unexpected fields or malformed roots raise `StubIndexInvalidException`.

`withLibraries(vararg packages: String): PhpStubs` resolves every package before mounting, preserving the supplied order. It mounts those roots with generated-set validation and no Vocabulary Mapping through the existing `extend` path. Unknown names raise `IllegalArgumentException`. The companion starts from the bundled lookup; an instance extends its own mounts. `with(roots)` and `with(dirs)` retain their existing behavior.

```kotlin
val lookup = PhpStubs.withLibraries("laravel/framework")
val record = lookup.method("Illuminate\\Database\\Query\\Builder::whereRaw")
val signature = record?.callableSignature
val sinks = record?.sinkFacts
```

### Resource layout

```text
taint-libraries/
  catalog.yaml
  summary.json
  laravel-framework/
    index.txt
    provenance.yaml
    laravel-framework.yaml
    rejections.json
    LICENSE-<upstream>.txt
```

Each selectable root holds one model document. Every callable entry has a Signature; each method's owner has a class Signature. `verification` is `generated`. The producer and document header name all contributing upstream identities. Each entry's `from` comment names its declaration and Fact origins. A rejection-only directory has no manifest and is absent from the catalog.

The build's `ProcessResources` action generates each selectable root's `index.txt`, as it does for the bundled roots. Source resources contain no per-root manifest; the importer excludes manifests from its output and comparison.

Each root carries the MIT notice for every upstream it uses. Where the supplied tree has only a license declaration, the importer constructs the MIT text using its declared authors.

## Function Specifications

### tools/import_library.py

`--upstreams DIRECTORY` supplies the inert checkouts: the five upstreams with endpoint lists and stubs and the nine pinned library releases below, one subdirectory per origin. `--resources DIRECTORY` selects the resource tree; it defaults to this repository's resources. `--check` regenerates in memory, compares every output file including notices and rejection lists, prints a unified diff and exits unsuccessfully on differences. Run with `python3 -I`; no upstream code is imported or executed.

Each library release is pinned in `UPSTREAMS`; the reader loads it before the upstream stubs, so an upstream stub declaration replaces the release declaration of the same class or method and keeps the trait uses of both. The catalog version of a package with a pinned release is that release's version.

| Origin | Package | Tag | Commit |
|---|---|---|---|
| `framework` | `laravel/framework` | v13.40.0 | 1449bf241017087fbd38c118ecaabef3f6797fdc |
| `dbal` | `doctrine/dbal` | 4.5.1 | b2815456989aa41964ee66d7ab47b7885264acf3 |
| `browsershot` | `spatie/browsershot` | 5.5.0 | eba71ab7f4aba23d9321d653ccd19d4e94432516 |
| `filesystem` | `symfony/filesystem` | v7.4.23 | 53d609da66578dad5a39fe290e8f924ec8f05e93 |
| `http-foundation` | `symfony/http-foundation` | v7.4.23 | 7fb73cffa06e2bcc2cb523fcccb1e8174106b206 |
| `framework-bundle` | `symfony/framework-bundle` | v7.4.23 | 6a749f2c37cb9def53793633ec72958aaad4b359 |
| `dom-crawler` | `symfony/dom-crawler` | v7.4.22 | cc5c3d6275873fd463c2a772251d65379015682f |
| `ldap` | `symfony/ldap` | v7.4.10 | bba9e535d29c15bd6842bf85bc341debfbb4bcb3 |
| `process` | `symfony/process` | v7.4.22 | a5a6912edbbfc4c98cd080bc4bbe37c8e7eeb20a |

A release's classes are the `.php` files named for a class under the `autoload.psr-4` directories of its `composer.json`, outside its `exclude-from-classmap` paths. Laravel and Symfony pins follow the line the other upstreams target: the framework version of the newest `psalm-plugin-laravel` stub directory, and the `^7.4` constraint of `phpstan-security`. `doctrine/dbal` is the newest stable release of the `^4.0` line that `phpstan-security` requires; `spatie/browsershot` is the newest stable release, because no other upstream states a line. The notices of a release are `LICENSE-<origin>.txt`.

The PHP reader tokenizes declarations in namespace and class scopes, resolves native types through namespace imports, and retains parameter order, scalar defaults, references and variadic status. It reads explicit endpoint tags from `.phpstub`, `.stubphp` and `.php` files. Non-scalar defaults retain optional status without a default value. The tokenizer skips attributes and reads heredoc and nowdoc bodies as one token; an unbraced namespace ends at the next `namespace` declaration, not at a `->namespace` or `::namespace` member access. PHPDoc virtual methods and executable handlers do not supply Signatures. Versioned framework stub directories load in numeric order after common declarations; optional integrations are excluded.

Class Signatures retain `parent` and `interfaces`, resolving names through the namespace and `use` imports. Interface extension lists use `interfaces`. Referenced owners with supplied declarations, including traits and interfaces, receive signed class records recursively. An unavailable parent keeps its name without an invented record; `summary.json` lists these names per package as `unrecordedParents`.

`ClassSignature` has no trait-use field. `expand_trait_members` retains the signed trait owners and expands their methods and Facts onto using owners, including nested traits and the supplied `as` aliases. A directly declared method takes precedence. Endpoint rows naming inherited members resolve against traits, the parent and interfaces; a resolved row receives its own signed method entry. `PhpStubs.method` remains an exact per-owner lookup; CobraPHP traverses native parent/interface relations. No trait is encoded as an interface.

The NEON reader accepts the supplied indentation and inline endpoint lists. A sink's parameter name resolves against the final Signature. Its `path` kind maps to both `pathtrav` and `ssrf`, matching the consuming rule's combined meaning. Function propagation declarations do not become sanitizers.

The CodeQL reader accepts inline MaD arrays for endpoint families. Untyped rows are rejected as `no-class`. A short class name resolves only when one declaration matches inside the identified package; declarations of the other upstreams are matched first, and the library releases only when none of those matches, so a release class such as a facade or contract with the same short name does not make the row ambiguous. Argument `-1` expands to every declared parameter; other argument indices must be within the Signature. Sanitizer rows without a vulnerability kind cannot establish a kind-specific sanitizer.

The importer owns the upstream kind tables and reads the shared Psalm mapping. It deduplicates by subject, section, port and canonical kind, retaining all contributing origins. Non-request sources map to `external-input`. Where one upstream declares a source and another explicitly declares the same member not a source, the union keeps the source: a missed flow costs more than a false one. In particular, `Illuminate\Http\Request::file` remains a `user-input` source.

Rejections retain subject, section, upstream, input location and reason: missing declarations, unresolved parameters, unsupported conditions or annotations, and kinds without a supported meaning. Constant cryptographic key checks are rejected as `not-taint-flow` before class or Signature checks; they do not describe source-to-sink flows. The summary counts emitted entries and Facts separately from rejections.

## Exception / Error Types

- `IllegalArgumentException`: unknown selected package.
- `StubIndexNotFoundException`: absent catalog or selected resource.
- `StubIndexInvalidException`: malformed catalog or invalid selected Document Set.
- Importer input errors fail the command before output is written; `--check` differences return a failing exit status.

## Open Gaps

- Fifty-one `laravel/framework` rows remain rejected as `no-signature`: the pinned release declares no method for the raw-clause methods that `Illuminate\Database\Eloquent\Builder` forwards through `__call` (8), `Illuminate\Support\Facades\Http` (6) and `Illuminate\Support\Facades\Request` (29). `Illuminate\Http\Request::validate` is declared only by a PHPDoc `@method` tag and a macro, and `validated` and `safe` are declared only on `Illuminate\Foundation\Http\FormRequest` (3). The short name `Storage` in the five `Storage` rows matches two release classes, `Illuminate\Container\Attributes\Storage` and `Illuminate\Support\Facades\Storage`, so the row stays unresolved (5). The other eight packages have no `no-signature` row.
- `expand_trait_members` copies a trait's methods and Facts onto every class that uses the trait in the loaded releases, so a Fact that an upstream states on a trait also appears on `Fluent`, `ComponentAttributeBag`, `UriQueryString` and `CommandInput`, which no upstream names and which are not request data.
- Facade `__callStatic` dispatch beyond explicitly declared subjects is not resolved by `read_psalm`.
- Receiver-state flows, such as constructing a raw clause and later executing a query, are not represented by imported endpoints; immediate sink annotations retain upstream approximations.
- Propagation rows and executable upstream handlers are not imported. Conditional sanitizer annotations remain rejected because generated entries must be unconditional.
- `withLibraries` does not select a version from `composer.lock`. Catalog versions record available evidence and can be unknown.
- Where an upstream stub and a pinned release declare the same method, the stub Signature is kept although the catalog version names the release. For `doctrine/dbal` 4.5.1, `Connection::prepare` carries the stub parameter `statement` (release: `sql`) and `Connection::quote` carries `input, type` (release: `value`). The `phpstan-security` row for `prepare` names the parameter `sql` and is rejected as `unresolved-parameter` for that reason; the stub sink on argument 0 covers it.
- `doctrine/orm` has no importable sink with a supplied matching declaration; the supplied Doctrine endpoint list covers DBAL only. The `unassigned-*` sets have no pinned release, so their `no-signature` rows stay rejected.
- `amphp/file` has function endpoints only. `psr/http-client` and `webklex/php-imap` have signed source records only; these packages cannot supply a signed method with a sink for testing.
- Optional integrations and PHPDoc virtual methods supply no Signatures. PHPDoc generics are not converted to native types. Non-scalar default expressions retain optional status without a default value.
- Eight distinct parents of emitted classes have no declaration in any supplied stub or release: two in `amphp/http-client`, one in `guzzlehttp/guzzle`, two in `jcupitt/vips`, and one each in `monolog/monolog`, `pear/archive_tar` and `phpoffice/phpspreadsheet`. Their named `parent` edges remain in Signatures; `summary.json` enumerates them. Missing interface or trait declarations likewise cannot supply inherited members.
