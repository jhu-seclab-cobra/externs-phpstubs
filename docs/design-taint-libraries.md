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

Each root carries the MIT notice for every upstream it uses. Where the supplied tree has only a license declaration, the importer constructs the MIT text using its declared authors.

## Function Specifications

### tools/import_library.py

`--upstreams DIRECTORY` supplies the five inert checkouts. `--resources DIRECTORY` selects the resource tree; it defaults to this repository's resources. `--check` regenerates in memory, compares every output file including notices and rejection lists, prints a unified diff and exits unsuccessfully on differences. Run with `python3 -I`; no upstream code is imported or executed.

The PHP reader tokenizes declarations in namespace and class scopes, resolves native types through namespace imports, and retains parameter order, scalar defaults, references and variadic status. It reads explicit endpoint tags from `.phpstub`, `.stubphp` and `.php` files. Non-scalar defaults retain optional status without a default value. PHPDoc virtual methods and executable handlers do not supply Signatures. Versioned framework stub directories load in numeric order after common declarations; optional integrations are excluded.

The NEON reader accepts the supplied indentation and inline endpoint lists. A sink's parameter name resolves against the final Signature. Its `path` kind maps to both `pathtrav` and `ssrf`, matching the consuming rule's combined meaning. Function propagation declarations do not become sanitizers.

The CodeQL reader accepts inline MaD arrays for endpoint families. Untyped rows are rejected as `no-class`. A short class name resolves only when one declaration matches inside the identified package. Argument `-1` expands to every declared parameter; other argument indices must be within the Signature. Sanitizer rows without a vulnerability kind cannot establish a kind-specific sanitizer.

The importer owns the upstream kind tables and reads the shared Psalm mapping. It deduplicates by subject, section, port and canonical kind, retaining all contributing origins. Non-request sources map to `external-input`. Rejections retain subject, section, upstream, input location and reason: missing declarations, unresolved parameters, unsupported conditions or annotations, and kinds without a supported meaning. The summary counts emitted entries and Facts separately from rejections.

## Exception / Error Types

- `IllegalArgumentException`: unknown selected package.
- `StubIndexNotFoundException`: absent catalog or selected resource.
- `StubIndexInvalidException`: malformed catalog or invalid selected Document Set.
- Importer input errors fail the command before output is written; `--check` differences return a failing exit status.

## Open Gaps

- Rows rejected as `no-signature` need declarations from additional pinned library releases before they can become active Facts.
- Facade `__callStatic` dispatch beyond explicitly declared subjects is not resolved by `read_psalm`.
- Receiver-state flows, such as constructing a raw clause and later executing a query, are not represented by imported endpoints; immediate sink annotations retain upstream approximations.
- Propagation rows and executable upstream handlers are not imported. Conditional sanitizer annotations remain rejected because generated entries must be unconditional.
- `withLibraries` does not select a version from `composer.lock`. Catalog versions record available evidence and can be unknown.
- Source-only packages have signed source records but no upstream sink to test or publish.
