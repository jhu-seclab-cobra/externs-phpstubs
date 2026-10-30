# PHP Stubs — Signature Extraction Design

The signature producer of the extraction design
([design-extraction.md](design-extraction.md)): `tools/extract_signatures.py`
and `tools/compile_facts.py`, with `tools/named_extras.py` for argument reception.
Its reception counts, binding admission, memory transport and admitted C
call-context APIs are in `named_extras_reception`, `named_extras_bindings`,
`named_extras_flow` and `named_extras_context`.
The tests: `tools/test_named_extras.py` (source patterns and extracted policies),
`BuiltinNamedExtrasTest` (bundled signature decoding), `tools/test_compile_facts.py`
(closure check, selection rule) and `OneOpcodeCompileTest` (the extracted
sets).

### extract_signatures.py

| Input | Yields |
|-------|--------|
| `**/*.stub.php` | each function and method: parameter names, declared types, by-reference, variadic, and default marks, the return type, the `@frameless-function` argument counts |
| `Zend/zend_compile.c`, `Zend/zend_string.h` | the by-name dispatch of function calls compiled to one opcode (`zend_try_compile_special_func_ex`), the operands of each compile function, and the known strings the dispatch names |
| `**/*_arginfo.h`, `**/*.{c,h,cpp,cc}` through `php_src_c.Program` | ordinary builtin handlers, argument parsing macros and their reception groups |

- A parameter is `optional` when it declares a default or is variadic, and
  `byRef` when declared `&` or tagged `@prefer-ref` in its doc comment
  (the interpreter passes such an argument by reference when it can).
- A parameter whose default is a scalar literal (`true`, `false`, `null`, an
  integer, a decimal, or a quoted string with no escape or interpolation) also
  carries that literal as `default`, spelled as in the stub; any other default
  (a constant, an array, an expression) leaves `default` absent. Format and
  meaning: [parameter facts](../../commons-phpmodels/docs/design-declarations.md).
- After selecting stub signature variants, `with_named_extras` reads one shared
  C program and attaches a source-established policy only to each callable's
  variadic parameter. Format and meaning:
  [parameter facts](../../commons-phpmodels/docs/design-declarations.md#namedextras).
- `named_extras.read_policies(program, keys)` resolves each subject through the
  shared registration tables, including aliases. Every ordinary handler and
  every definition must agree. Frameless handlers do not receive named calls.
- `Z_PARAM_VARIADIC` and `Z_PARAM_VARIADIC_EX` establish rejection in a plain,
  unconditional parsing group. The reception position counts preceding
  argument-consuming macro prologues, following source macro aliases. The shared
  C parser and CFG compiler read each expanded macro in its parsing-group break
  scope. All reachable exits must pass the same unconditional prologues. Macro
  arguments are substituted before effects are read. An assignment or
  update of the counter outside the admitted prologue, an escaped counter
  address, conditional count, residual macro or unread statement is unknown.
  Assignment nodes cover direct and compound assignments uniformly. The count
  is not inferred from the stub's variadic index: `array_map` records 1, because
  its callback precedes the group including its first array.
- `Z_PARAM_VARIADIC_WITH_NAMED` establishes forwarding when its preserved named
  arguments reach `zend_call_known_function`, `zend_call_known_fcc` or
  `zend_call_function` on a reached path. `Forwarding` reuses the shared C
  compiler, source index, abstract machine and region memory. Its incoming call
  frame holds the original named collection; the parsing group reads that same
  input. Before compilation, the signature producer conservatively requires
  unshadowed lexical declarations, including parameters, enclosing references,
  nested blocks and for scopes. Visibility and lifetime follow the
  [shared compiler and machine](design-extraction-handlers.md#class--type-specifications).
  A reference after a conditional-compilation group retains each configuration's
  binding, including the enclosing binding when a branch declares no local or
  the group has no else branch. Subsequent instructions, child scopes and
  suspended-instruction retries preserve those alternatives and their correlation.
  Selecting one configuration cannot replace another configuration's binding.
  Shadowing in a transport body leaves forwarding unestablished.
  Helper calls and aliases share memory, and writes into the collection
  invalidate its preservation. Returns and false branches reach no target.
  Unread calls invalidate passed memory and the proof, even when their result
  is unused. Thin helpers bind their literal arguments in the machine, so
  subsequent assignments determine their branch selection.
- C call-context summaries are source-admitted APIs, not builtin names. A
  constructor selector requires its declared handler ABI, admitted source, and
  the same object produced by a successful admitted object initializer. Known
  selector targets run their body. Context initialization binds its selected
  source entry to an opaque handle; resumption requires that same binding and
  supplies its active fiber and transfer context. Body and expanded-body digests
  admit these contracts and the read-only INI getter forms. Literal ASCII strlen
  is folded only without a source override. Changed protocol bodies are
  unestablished. Local definitions never inherit a native summary. Initial
  external setjmp returns zero; a non-local jump reaches no following instruction.
- The working-state bound of reception counting and the existing C machine's
  request budget leave unestablished proofs null. They add no analyzer state.
- Whitespace-collapsed digests check the parsing primitives of `zend_API.h`.
  A changed primitive, missing/conflicting definition, unread reception,
  optional or conditional rejecting group, earlier control flow, unread parsing block, recursive
  helper or unproved forwarding leaves the policy null. No variadic default
  asserts rejection. `imagefilter` dispatches to filter-specific parsing
  without a recognized variadic group and remains null (accept-and-ignore).
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
