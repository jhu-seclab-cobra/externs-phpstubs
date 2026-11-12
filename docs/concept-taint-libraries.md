# Library Taint Facts

## Context

Applications can call third-party libraries whose implementation is absent from the analyzed code. A builtin-only lookup cannot identify the sinks, sources and sanitizers at those calls. Library declarations let the lookup answer a Signature and the associated Facts together.

This module supplies selectable Document Sets to the existing lookup.

- **Inputs:** Signatures and endpoint annotations [@psalm-plugin-laravel; @psalm-plugin-doctrine; @psalm7], named-parameter endpoint lists [@phpstan-security], and class-qualified endpoint rows [@codeql-php].
- **Outputs:** Records with a Signature in the Canonical Vocabulary.
- **Connections:** Upstream declarations and Facts → Library Set → Set Merge → builtin lookup.
- **Owned:** Importing, package selection, attribution, notices and explicit rejection of unsupported input.
- **Not Owned:** Executing library bodies, resolving application facades, or selecting a version from application dependencies.

## Concepts

```text
Declarations + endpoint lists
             |
        Library Set
             |
         Set Merge
             |
      Signature + Facts
```

- **Name:** [Library Set](glossary/glossary-lookup.md#library-set).
- **Role:** Select library declarations and Facts using the application's package names.
- **Scope:** One package's supported endpoints; it does not represent the whole implementation.
- **Relationships:** A Library Set is a generated Document Set whose Facts use the Canonical Vocabulary.

A source read from files, stored records or another server uses `external-input`; request input uses `user-input`. Importing an annotation establishes its origin, without establishing an independently verified security guarantee.

## Contracts & Flow

**With the builtin lookup:** Each emitted callable and its owner has a Signature. A Fact with no matching declaration is rejected rather than published as an inactive record.

**With Set Merge:** All upstream Facts for a package are combined before mounting. This preserves the [whole-unit replacement contract](spec-merge.md) when several upstreams describe the same endpoint.

The [design](design-taint-libraries.md) owns catalog selection, the importer and the output layout.

## Scenarios

- **Typical:** An application selects a database library, and a raw-query call resolves to a method record with a Signature and a SQL injection sink on its SQL argument.
- **Boundary:** An upstream lists a method absent from the supplied declarations. Its row remains in the rejection list and contributes no active Fact.
- **Interaction:** A consumer mounts manual corrections after library selection; Set Merge retains the manual unit in force.

## Rationale and Rejected Alternatives

One set per package matches the application's dependency identity. Separate sets per upstream would replace each other's Facts when both describe the same subject and assertion unit. Combining Facts before emission keeps different vulnerability types on one port while removing exact duplicates.
