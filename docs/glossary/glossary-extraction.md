# Glossary — C extraction

## Callable implementations

### Handler
- **Definition:** A C function registered as an implementation target of a PHP builtin callable.
- **Example:** An ordinary and a frameless function entry → distinct Handler targets for the callable.
- **Source:** `tools/php_src_c/registrations.py` `Program`; `docs/concept-extraction.md` Core Concepts

### Boundary Call
- **Definition:** A C call whose own exceptions the builtin throws assertion excludes, apart from explicitly admitted argument-value checks.
- **Example:** Argument parsing with `Z_PARAM_PATH` → its admitted NUL-byte check contributes `ValueError` without entering the argument-binding implementation.
- **Source:** `tools/extract_throws.py` `Evaluation` `is_boundary` `specifier_classes`; `docs/spec-throws.md`

## Summaries

### Procedure Summary
- **Definition:** A finite summary of the guarded throw, object-creation and class-return effects of one C function.
- **Example:** A helper that throws its class-entry parameter → a guarded class-parameter element instantiated by the caller.
- **Source:** `tools/extract_throws.py` `Summary` `Evaluation`; `tools/php_src_c/definitions.py` `ProcedureSummaries`; `docs/spec-throws.md`
