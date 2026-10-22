# PHP Stubs — Signature Extraction Design

The signature producer of the extraction design
([design-extraction.md](design-extraction.md)): `tools/extract_signatures.py`
and `tools/compile_facts.py`. The tests: `tools/test_compile_facts.py`
(closure check, selection rule) and `OneOpcodeCompileTest` (the extracted
sets).

### extract_signatures.py

| Input | Yields |
|-------|--------|
| `**/*.stub.php` | each function and method: parameter names, declared types, by-reference, variadic, and default marks, the return type, the `@frameless-function` argument counts |
| `Zend/zend_compile.c`, `Zend/zend_string.h` | the by-name dispatch of function calls compiled to one opcode (`zend_try_compile_special_func_ex`), the operands of each compile function, and the known strings the dispatch names |

- A parameter is `optional` when it declares a default or is variadic, and
  `byRef` when declared `&` or tagged `@prefer-ref` in its doc comment
  (the interpreter passes such an argument by reference when it can).
- `frameless_counts` applies php-src
  `find_frameless_function_info` to the function's `@frameless-function`
  tags: a count c from 0 to 3 is listed when the first tag whose arity is at
  least c (exactly c for a variadic function) exists and the function
  requires at most c parameters.
- `special_count` lists the argument counts, 2 or more, at which
  `zend_try_compile_special_func_ex` always compiles a call to one opcode:
  `array_key_exists` with 2 (`ZEND_ARRAY_KEY_EXISTS` of `args->child[0]` and
  `args->child[1]`; its operands must agree with its argument count check).
- `rope_position` is the format parameter of `zend_compile_func_sprintf`:
  `sprintf` `format`, the parameter at the argument position whose constant
  value the compile function folds.
- **Closure check.** Every target of `zend_try_compile_special_func_ex` has
  a recorded disposition: special counts, at most one operand, constant
  operands besides one, arguments read where they stand, the rope, or the
  merged `call_user_func_array` form. The extractor keeps comment-stripped
  digests of `zend_try_compile_special_func`,
  `zend_try_compile_special_func_ex`, `find_frameless_function_info`,
  `zend_compile_frameless_icall_ex`, `zend_compile_ns_call`,
  `zend_compile_func_cufa` and every target, and resolves each `ZSTR_KNOWN`
  name against `Zend/zend_string.h`. An unknown target, an unresolved name
  or a changed digest fails the run.
- A type php-src omits is `mixed`, PHP's reading of an omitted type. A
  class name in a type is resolved and keeps its spelling.
- A declaration stated in several conditional-compilation variants keeps
  the variant that subsumes the other: it admits every call the other
  admits and its return type includes the other's. Neither subsuming
  fails the run.
- Each generated function or method entry php-src declares is relocated
  to its extension, then gets the subject line and signature block
  php-src states; its other sections (propagation, throws) stay, except a
  propagation element naming an argument position the signature lacks
  (no variadic parameter): PHP rejects a call passing more arguments
  than an internal function declares (`ArgumentCountError`), so no value
  reaches that position. A propagation section left without an element
  fails the run.
- A php-src function no models document declares joins `placement` of its
  extension; a method joins the generated document declaring its class,
  and a class no generated document declares fails the run.
