# PHP Stubs — Library Set import

## Problem

Read inert upstream declarations and endpoint lists and produce one [Library Set](glossary/glossary-lookup.md#library-set) per selectable package, a catalog, notices, rejections and counts. A published Fact must resolve to a declaration with a Signature and use the Canonical Vocabulary. The importer executes no upstream code.

## Steps

1. The PHP reader tokenizes declarations in namespace and class scopes, resolves native types through namespace imports, and retains parameter order, scalar defaults, references and variadic status. It reads explicit endpoint tags from `.phpstub`, `.stubphp` and `.php` files. Non-scalar defaults retain optional status without a default value. The tokenizer skips attributes and reads heredoc and nowdoc bodies as one token; an unbraced namespace ends at the next `namespace` declaration, not at a `->namespace` or `::namespace` member access. PHPDoc virtual methods and executable handlers do not supply Signatures. Versioned framework stub directories load in numeric order after common declarations; optional integrations are excluded.

2. Class Signatures retain `parent` and `interfaces`, resolving names through the namespace and `use` imports. Interface extension lists use `interfaces`. Referenced owners with supplied declarations, including traits and interfaces, receive class records with a Signature recursively. An unavailable parent keeps its name without an invented record; `summary.json` lists these names per package as `unrecordedParents`.

3. `ClassSignature` has no trait-use field. `expand_trait_members` retains the trait owners with a Signature and expands their methods onto using owners, including nested traits and the supplied `as` aliases. A sink or sanitizer Fact is copied onto every using owner, because it states what the method body does. A source Fact is copied only onto a using owner that an upstream names, by a class declaration in a stub or by an endpoint row, because it states what data the object holds, and that differs per class. A directly declared method takes precedence. Endpoint rows naming inherited members resolve against traits, the parent and interfaces; a resolved row receives its own method entry with a Signature. `PhpStubs.method` remains an exact per-owner lookup; callers traverse parent/interface relations under their own lookup semantics. No trait is encoded as an interface.

4. The NEON reader accepts the supplied indentation and inline endpoint lists. A sink's parameter name resolves against the final Signature. Its `path` kind maps to both `pathtrav` and `ssrf`, matching the consuming rule's combined meaning. Function propagation declarations do not become sanitizers.

5. The CodeQL reader accepts inline MaD arrays for endpoint families. Untyped rows are rejected as `no-class`. A short class name resolves only when one declaration matches inside the identified package; declarations of the other upstreams are matched first, and the library releases only when none of those matches, so a release class such as a facade or contract with the same short name does not make the row ambiguous. Argument `-1` expands to every declared parameter; other argument indices must be within the Signature. Sanitizer rows without a vulnerability kind cannot establish a kind-specific sanitizer.

6. The importer owns the upstream kind tables and reads the shared Psalm mapping. It deduplicates by subject, section, port and canonical kind, retaining all contributing origins. Non-request sources map to `external-input`. Where one upstream declares a source and another explicitly declares the same member not a source, the union keeps the source: a missed flow costs more than a false one. In particular, `Illuminate\Http\Request::file` remains a `user-input` source.

7. Rejections retain subject, section, upstream, input location and reason: missing declarations, unresolved parameters, unsupported conditions or annotations, and kinds without a supported meaning. Constant cryptographic key checks are rejected as `not-taint-flow` before class or Signature checks; they do not describe source-to-sink flows. The summary counts emitted entries and Facts separately from rejections.

## Invariants

- Every emitted callable and each method owner has a Signature.
- Every retained endpoint row resolves its parameter to the final Signature.
- Facts from different upstreams are combined before a whole replacement unit is mounted.
- Rejected input contributes no active Fact and retains its origin and reason.

## Termination

The supplied trees, declarations and endpoint rows are finite. Trait expansion follows the finite supplied declaration graph; directly declared methods terminate resolution before inherited candidates. Unsupported inputs are rejected rather than followed into executable code.

## Complexity

For S supplied source bytes, W declaration/trait/endpoint resolution and combination work, and R emitted bytes, time is O(S + W + R). Space retains input declarations D, candidate rows C and emitted output R, O(D + C + R). W includes inherited-member searches and does not claim a source-linear bound.

## Example

```php
<?php
function query(\Illuminate\Database\Query\Builder $builder, string $sql): void {
    $builder->whereRaw($sql);
}
```

Selecting `laravel/framework` makes the supplied declaration and SQL injection sink Fact for `whereRaw` available together. Import does not execute the method or infer the application’s installed version.
