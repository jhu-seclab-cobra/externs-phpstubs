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

**Responsibility:** Public data class in module `externs-phpstubs`, package `edu.jhu.cobra.externs.phpstubs`, holding catalog metadata.

**State:** A catalog row contains `package` (exact Composer name), `version` (the version or constraint the stubs describe, or `unknown`), `upstreams` (source names with release identities), and `root` (classpath directory). A major line or constraint is not an exact installed release.

### PhpStubs

**Responsibility:** Public lookup composition API in module `externs-phpstubs`; its selected mounts remain instance-owned.

`libraries: List<LibrarySet>` reads the machine-readable catalog lazily. Duplicate package names, unexpected fields or malformed roots raise `StubIndexInvalidException`.

`withLibraries(vararg packages: String): PhpStubs` resolves every package before mounting, preserving the supplied order. It mounts those roots with generated-set validation and no Vocabulary Mapping through the existing `extend` path. Unknown names raise `IllegalArgumentException`. The companion starts from the bundled lookup; an instance extends its own mounts. `with(roots)` and `with(dirs)` retain their existing behavior.



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

`--upstreams DIRECTORY` supplies the inert checkouts: the five upstreams with endpoint lists and stubs and the nine pinned library releases in the bibliography, one subdirectory per origin. `--resources DIRECTORY` selects the resource tree; it defaults to this repository's resources. `--check` regenerates in memory, compares every output file including notices and rejection lists, prints a unified diff and exits unsuccessfully on differences. Run with `python3 -I`; no upstream code is imported or executed.

Each library release is pinned in `UPSTREAMS`; the reader loads it before the upstream stubs, so an upstream stub declaration replaces the release declaration of the same class or method and keeps the trait uses of both. The catalog version of a package with a pinned release is that release's version.

Pinned declaration sources: [@library-framework; @library-dbal; @library-browsershot; @library-filesystem; @library-http-foundation; @library-framework-bundle; @library-dom-crawler; @library-ldap; @library-process]. Package/version metadata is retained in the catalog; immutable source identities are in the bibliography.

A release's classes are the `.php` files named for a class under the `autoload.psr-4` directories of its `composer.json`, outside its `exclude-from-classmap` paths. Laravel and Symfony pins follow the line the other upstreams target: the highest-numbered framework stub directory in the supplied `psalm-plugin-laravel` tree, and the `^7.4` constraint of `phpstan-security`. `doctrine/dbal` is the selected release of the `^4.0` line that `phpstan-security` requires; `spatie/browsershot` is selected without a constrained major line because no other upstream states a line. The notices of a release are `LICENSE-<origin>.txt`.

The import algorithm, endpoint resolution and Fact combination are specified by [Library Set import](spec-taint-libraries.md).

## Exception / Error Types

- `IllegalArgumentException`: unknown selected package.
- `StubIndexNotFoundException`: absent catalog or selected resource.
- `StubIndexInvalidException`: malformed catalog or invalid selected Document Set.
- Importer input errors fail the command before output is written; `--check` differences return a failing exit status.

## Caller Examples

```kotlin
import edu.jhu.cobra.externs.phpstubs.PhpStubs
import edu.jhu.cobra.externs.phpstubs.callableSignature

val lookup = PhpStubs.withLibraries("laravel/framework")
val record = lookup.method("Illuminate\\Database\\Query\\Builder::whereRaw")
println(record?.callableSignature)
println(record?.sinkFacts)
```

## Open Gaps

- How should dynamic endpoints without native declarations be represented? Fifty-one `laravel/framework` rows remain rejected as `no-signature`: the pinned release declares no method for the raw-clause methods that `Illuminate\Database\Eloquent\Builder` forwards through `__call` (8), `Illuminate\Support\Facades\Http` (6) and `Illuminate\Support\Facades\Request` (29). `Illuminate\Http\Request::validate` is declared only by a PHPDoc `@method` tag and a macro, and `validated` and `safe` are declared only on `Illuminate\Foundation\Http\FormRequest` (3). The short name `Storage` in the five `Storage` rows matches two release classes, `Illuminate\Container\Attributes\Storage` and `Illuminate\Support\Facades\Storage`, so the row stays unresolved (5). The other eight packages have no `no-signature` row.
- Which additional using classes have evidence of request data? A trait source Fact reaches only the using classes an upstream names, so the data holders `Fluent`, `ComponentAttributeBag`, `UriQueryString` and `CommandInput` of `laravel/framework` get no `InteractsWithData` source: no upstream says they hold request data, and they are generic containers, template attributes, query strings of any URI and console arguments. A request-derived instance of these classes is therefore not a source. Trait sink Facts are copied onto unnamed using classes as well, for example the header sinks on `Illuminate\Http\JsonResponse`.
- How should facade dispatch without an explicit declaration be represented? Facade `__callStatic` dispatch beyond explicitly declared subjects is not resolved by `read_psalm`.
- How should receiver-state flows be represented? Receiver-state flows, such as constructing a raw clause and later executing a query, are not represented by imported endpoints; immediate sink annotations retain upstream approximations.
- How should conditional annotations and propagation input be imported? Propagation rows and executable upstream handlers are not imported. Conditional sanitizer annotations remain rejected because generated entries must be unconditional.
- How should application version selection be provided if required? `withLibraries` does not select a version from `composer.lock`. Catalog versions record available evidence and can be unknown.
- Which declaration should govern parameter names when supplied sources disagree? Where an upstream stub and a pinned release declare the same method, the stub Signature is kept although the catalog version names the release. For `doctrine/dbal` 4.5.1, `Connection::prepare` carries the stub parameter `statement` (release: `sql`) and `Connection::quote` carries `input, type` (release: `value`). The `phpstan-security` row for `prepare` names the parameter `sql` and is rejected as `unresolved-parameter` for that reason; the stub sink on argument 0 covers it.
- What declaration source can resolve the currently unassigned endpoints? `doctrine/orm` has no importable sink with a supplied matching declaration; the supplied Doctrine endpoint list covers DBAL only. The `unassigned-*` sets have no pinned release, so their `no-signature` rows stay rejected.
- Which package data can provide a sink-bearing method when required for acceptance? `amphp/file` has function endpoints only. `psr/http-client` and `webklex/php-imap` have source records with a Signature only; these packages cannot supply a method record with a Signature and a sink for testing.
- Which additional declaration/type forms should the importer admit? Optional integrations and PHPDoc virtual methods supply no Signatures. PHPDoc generics are not converted to native types. Non-scalar default expressions retain optional status without a default value.
- Which supplied source can provide the missing inherited declarations? Eight distinct parents of emitted classes have no declaration in any supplied stub or release: two in `amphp/http-client`, one in `guzzlehttp/guzzle`, two in `jcupitt/vips`, and one each in `monolog/monolog`, `pear/archive_tar` and `phpoffice/phpspreadsheet`. Their named `parent` edges remain in Signatures; `summary.json` enumerates them. Missing interface or trait declarations likewise cannot supply inherited members.
