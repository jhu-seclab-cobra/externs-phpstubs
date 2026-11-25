# PHP Stubs — Signature extraction design

## Design Overview

- **Modules:** `extract_signatures`, `extract_members`, `compile_facts`, `named_extras` and its reception, bindings, flow and context modules.
- **Relationships:** The signature producer reads the shared C program and compiler sources; the named-extra helpers reuse the C compiler and machine specified in [handler design](design-extraction-handlers.md).
- **Exceptions:** `ExtractionFailure` from malformed mandatory input, conflicting declarations or changed admitted compiler bodies.
- **Dependency roles:** Source/placement/writing: `php_src`. Compiler facts: `compile_facts`. Argument reception: `named_extras`.

## Function Specifications

### Signature producer

`extract_signatures.main()` takes `--php-src` and `--models`, reads source stubs and compiler/native reception inputs, and rewrites callable Signature fields in place. A successful second run over the same inputs writes identical bytes. It preserves unrelated sections; source admission, parameter defaults, arities, conditional variants and field preservation follow [Signature extraction](spec-extraction-signatures.md).

`named_extras.read_policies(program, keys)` consumes the shared C program and callable keys and returns source-established policies for variadic parameters. An unproved optional policy is absent; mandatory source failures propagate `ExtractionFailure`. Its component modules own reception counts, binding admission, memory transport and admitted call-context APIs.

### Member producer

`extract_members.main()` takes `--php-src` and `--models` and adds the property and class constant entries php-src declares with a type; a second run over its own output changes nothing.

- **Entries:** one `property` or `class_constant` entry per declaration with a declared type, whose signature holds the type, resolved as `extract_signatures.py` resolves a parameter type. A property also holds its visibility and, when static, `static: true`. A class constant states no value: the stubs mostly give a C macro, so a record without `typedSignature.value` is a constant of that type with an unknown value. A declaration without a type, a method and an enum case give no entry, because a redeclaration of an untyped member is not checked against a type. A private member keeps its entry; a class constant has no visibility field.
- **Placement:** as for a method: a generated entry php-src declares moves to the document of its php-src extension, a declaration no document holds joins the generated document declaring its class, and a generated entry has its signature rewritten with every other line untouched.
- **Identity:** the key folds the class of a member and keeps the member name, as PHP compares a constant or property name case-sensitively (`php_src.identity`); `SNMP::VERSION_2C` and `SNMP::VERSION_2c` are two entries.
- **Fails** with `ExtractionFailure` when two declarations of one member differ in type, visibility or staticness, when the class of a member is declared by no generated document, or when a property declaration no rule reads.

## Exception / Error Types

`ExtractionFailure` names malformed source, incompatible declarations, an unresolved mandatory source symbol, or a changed admitted body. The [extraction design](design-extraction.md#exception--error-types) owns shared error classification.

## Caller Examples

```text
python3 tools/extract_signatures.py --php-src /path/to/php-src --models /path/to/models-copy
python3 tools/extract_members.py --php-src /path/to/php-src --models /path/to/models-copy
```

The commands consume the hierarchy producer’s output. Verify emitted Signatures through the existing model decoder; the test owners are `tools/test_extract_members.py`, `MemberSignaturesTest`, `tools/test_named_extras.py`, `BuiltinNamedExtrasTest`, `tools/test_compile_facts.py` and `OneOpcodeCompileTest`.
