# PHP Stubs — Signature extraction design

## Design Overview

- **Modules:** `extract_signatures`, `compile_facts`, `named_extras` and its reception, bindings, flow and context modules.
- **Relationships:** The signature producer reads the shared C program and compiler sources; the named-extra helpers reuse the C compiler and machine specified in [handler design](design-extraction-handlers.md).
- **Exceptions:** `ExtractionFailure` from malformed mandatory input, conflicting declarations or changed admitted compiler bodies.
- **Dependency roles:** Source/placement/writing: `php_src`. Compiler facts: `compile_facts`. Argument reception: `named_extras`.

## Function Specifications

### Signature producer

`extract_signatures.main()` takes `--php-src` and `--models`, reads source stubs and compiler/native reception inputs, and rewrites callable Signature fields in place. A successful second run over the same inputs writes identical bytes. It preserves unrelated sections; source admission, parameter defaults, arities, conditional variants and field preservation follow [Signature extraction](spec-extraction-signatures.md).

`named_extras.read_policies(program, keys)` consumes the shared C program and callable keys and returns source-established policies for variadic parameters. An unproved optional policy is absent; mandatory source failures propagate `ExtractionFailure`. Its component modules own reception counts, binding admission, memory transport and admitted call-context APIs.

## Exception / Error Types

`ExtractionFailure` names malformed source, incompatible declarations, an unresolved mandatory source symbol, or a changed admitted body. The [extraction design](design-extraction.md#exception--error-types) owns shared error classification.

## Caller Examples

```text
python3 tools/extract_signatures.py --php-src /path/to/php-src --models /path/to/models-copy
```

The command consumes the hierarchy producer’s output. Verify emitted Signatures through the existing model decoder; the test owners are `tools/test_named_extras.py`, `BuiltinNamedExtrasTest`, `tools/test_compile_facts.py` and `OneOpcodeCompileTest`.
