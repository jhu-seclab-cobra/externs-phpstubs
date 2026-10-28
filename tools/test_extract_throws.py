"""Tests for extract_throws.py: the throws output stays what it was when the C reader moved to php_src_c.

Run: python3 -B -m unittest discover -s tools -p "test_*.py" (from the externs-phpstubs root).
- a throw primitive, a helper chain, a class parameter, a binding specifier and an object the caller supplies
- both branches of a conditional, a macro-defined function, file-local resolution of a static helper
- a class expression no rule resolves and a Handler no definition defines fail the run
- the command line rewrites the throws line of an entry and leaves every other line, the hierarchy-owned signature
  fields (final status and handler tables) included
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import extract_throws
import php_src

OPERATORS_H = """
ZEND_API void convert_to_long(zval *op);
#define zval_get_long(op) _zval_get_long(op)
"""

EXCEPTIONS_ARGINFO = """
static zend_class_entry *register_class_Error(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Error", class_Error_methods);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_TypeError(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "TypeError", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_ValueError(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "ValueError", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
"""

EXCEPTIONS_C = """
void zend_register_default_exception(void)
{
	zend_ce_error = register_class_Error();
	zend_ce_type_error = register_class_TypeError();
	zend_ce_value_error = register_class_ValueError();
}
"""

FOO_ARGINFO = """
static ZEND_FUNCTION(foo_plain);
static ZEND_FUNCTION(foo_helper);
static ZEND_FUNCTION(foo_param);
static ZEND_FUNCTION(foo_path);
static ZEND_FUNCTION(foo_conditional);
static ZEND_FUNCTION(foo_macro);
static ZEND_FUNCTION(foo_local);
static ZEND_FUNCTION(foo_open);
static ZEND_FUNCTION(foo_quiet);
static ZEND_METHOD(Foo, run);
static const zend_function_entry ext_functions[] = {
	ZEND_FE(foo_plain, arginfo_foo_plain)
	ZEND_FE(foo_helper, arginfo_foo_helper)
	ZEND_FE(foo_param, arginfo_foo_param)
	ZEND_FE(foo_path, arginfo_foo_path)
	ZEND_FE(foo_conditional, arginfo_foo_conditional)
	ZEND_FE(foo_macro, arginfo_foo_macro)
	ZEND_FE(foo_local, arginfo_foo_local)
	ZEND_FE(foo_open, arginfo_foo_open)
	ZEND_FE(foo_quiet, arginfo_foo_quiet)
	ZEND_FE_END
};
static const zend_function_entry class_Foo_methods[] = {
	ZEND_ME(Foo, run, arginfo_class_Foo_run, ZEND_ACC_PUBLIC)
	ZEND_FE_END
};
static zend_class_entry *register_class_Foo(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Foo", class_Foo_methods);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
"""

FOO_C = """
#include "foo_arginfo.h"
#define DEFINE_THROWER(name, ce) static void name(void) { zend_throw_error(ce, "thrown"); }
DEFINE_THROWER(thrower, zend_ce_value_error)

static void raise(zend_class_entry *ce)
{
	zend_throw_exception_zstr(ce, NULL, 0);
}
static void inner(void)
{
	zend_throw_error(zend_ce_type_error, "inner");
}
static void outer(void)
{
	inner();
}
static void helper(void)
{
	return;
}
ZEND_FUNCTION(foo_plain)
{
	zend_throw_error(zend_ce_type_error, "plain");
}
ZEND_FUNCTION(foo_helper)
{
	outer();
}
ZEND_FUNCTION(foo_param)
{
	raise(zend_ce_value_error);
}
ZEND_FUNCTION(foo_path)
{
	char *path;
	size_t len;
	ZEND_PARSE_PARAMETERS_START(1, 1)
		Z_PARAM_PATH(path, len)
	ZEND_PARSE_PARAMETERS_END();
}
ZEND_FUNCTION(foo_conditional)
{
#ifdef ZEND_WIN32
	zend_throw_error(zend_ce_type_error, "windows");
#else
	zend_throw_error(zend_ce_value_error, "elsewhere");
#endif
}
ZEND_FUNCTION(foo_macro)
{
	thrower();
}
ZEND_FUNCTION(foo_local)
{
	helper();
}
ZEND_FUNCTION(foo_open)
{
	zval *object;
	zend_throw_exception_object(object);
}
ZEND_FUNCTION(foo_quiet)
{
	zend_error(E_WARNING, "only a diagnostic");
}
ZEND_METHOD(Foo, run)
{
	zend_throw_error(NULL, "method");
}
"""

BAR_C = """
static void helper(void)
{
	zend_throw_error(zend_ce_type_error, "the other helper");
}
static void bar_user(void)
{
	helper();
}
"""

MODELS = """# Generated from stubs.
- subject:
    class: error
  signature:
    classifier: class
- subject:
    class: typeerror
  signature:
    classifier: class
    parent: error
- subject:
    class: valueerror
  signature:
    classifier: class
    parent: error
- subject:
    function: foo_plain
  signature:
    returnType: void
  throws: [stale]
- subject:
    function: foo_open
  signature:
    returnType: void
- subject:
    function: other
  signature:
    returnType: void
"""


def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def tree(root, **extra):
    write(root, "Zend/zend_operators.h", OPERATORS_H)
    write(root, "Zend/zend_exceptions_arginfo.h", EXCEPTIONS_ARGINFO)
    write(root, "Zend/zend_exceptions.c", EXCEPTIONS_C)
    write(root, "ext/foo/foo_arginfo.h", FOO_ARGINFO)
    write(root, "ext/foo/foo.c", FOO_C)
    write(root, "ext/bar/bar.c", BAR_C)
    for name, text in extra.items():
        write(root, name, text)


class ThrowsPinTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        tree(self.root)

    def tearDown(self):
        self.directory.cleanup()

    def throws(self):
        program = extract_throws.Program(self.root)
        return extract_throws.throws_of(program, program.entries())

    def test_entries_name_function_and_method_handlers(self):
        entries = extract_throws.Program(self.root).entries()
        self.assertEqual({"zif_foo_plain"}, entries[("function", "foo_plain")])
        self.assertEqual({"zim_Foo_run"}, entries[("method", "foo::run")])

    def test_direct_throw_helper_chain_and_class_parameter(self):
        found = self.throws()
        self.assertEqual(["typeerror"], found[("function", "foo_plain")])
        self.assertEqual(["typeerror"], found[("function", "foo_helper")])
        self.assertEqual(["valueerror"], found[("function", "foo_param")])

    def test_binding_specifier_throws_its_class(self):
        self.assertEqual(["valueerror"], self.throws()[("function", "foo_path")])

    def test_every_branch_of_a_conditional_counts(self):
        self.assertEqual(["typeerror", "valueerror"], self.throws()[("function", "foo_conditional")])

    def test_function_defining_macro_is_expanded(self):
        self.assertEqual(["valueerror"], self.throws()[("function", "foo_macro")])

    def test_static_helper_resolves_in_its_own_file(self):
        self.assertEqual([], self.throws()[("function", "foo_local")])

    def test_object_the_caller_supplies_is_open(self):
        self.assertIsNone(self.throws()[("function", "foo_open")])

    def test_diagnostic_alone_throws_nothing(self):
        self.assertEqual([], self.throws()[("function", "foo_quiet")])

    def test_null_class_defaults_to_error(self):
        self.assertEqual(["error"], self.throws()[("method", "foo::run")])

    def test_unresolved_class_expression_fails(self):
        write(self.root, "ext/foo/foo.c", FOO_C.replace("zend_ce_type_error, \"plain\"", "mystery_class, \"plain\""))
        with self.assertRaisesRegex(php_src.ExtractionFailure, "class expressions no rule resolves"):
            self.throws()

    def test_handler_without_definition_fails(self):
        write(self.root, "ext/foo/foo.c", FOO_C.replace("ZEND_FUNCTION(foo_plain)", "ZEND_FUNCTION(foo_other)"))
        with self.assertRaisesRegex(php_src.ExtractionFailure, "zif_foo_plain"):
            self.throws()


class ThrowsCommandTest(unittest.TestCase):
    def test_main_rewrites_throws_lines_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root, models = Path(directory) / "src", Path(directory) / "models"
            tree(root)
            write(models, "core.yaml", MODELS)
            argv, sys.argv = sys.argv, ["extract_throws.py", "--php-src", str(root), "--models", str(models)]
            try:
                with redirect_stdout(io.StringIO()) as out:
                    extract_throws.main()
            finally:
                sys.argv = argv
            text = (models / "core.yaml").read_text(encoding="utf-8")
            self.assertIn("function: foo_plain\n  signature:\n    returnType: void\n  throws: [typeerror]\n", text)
            self.assertNotIn("stale", text)
            self.assertIn("function: foo_open\n  signature:\n    returnType: void\n- subject:", text)
            self.assertIn("function: other\n  signature:\n    returnType: void\n", text)
            self.assertIn("foo_open", out.getvalue())
            before = text
            with redirect_stdout(io.StringIO()):
                sys.argv = ["extract_throws.py", "--php-src", str(root), "--models", str(models)]
                try:
                    extract_throws.main()
                finally:
                    sys.argv = argv
            self.assertEqual(before, (models / "core.yaml").read_text(encoding="utf-8"))


class ThrowsKeepsHierarchyFieldsTest(unittest.TestCase):
    def test_final_status_and_handler_tables_survive_the_throws_rewrite(self):
        plain = "function: foo_plain\n  signature:\n    returnType: void\n"
        kept = "    isFinal: true\n    handlers:\n    - id: ext/real/real.c:t_handlers\n      facts: []\n"
        with tempfile.TemporaryDirectory() as directory:
            root, models = Path(directory) / "src", Path(directory) / "models"
            tree(root)
            write(models, "core.yaml", MODELS.replace(plain, plain + kept))
            argv, sys.argv = sys.argv, ["extract_throws.py", "--php-src", str(root), "--models", str(models)]
            try:
                with redirect_stdout(io.StringIO()):
                    extract_throws.main()
            finally:
                sys.argv = argv
            text = (models / "core.yaml").read_text(encoding="utf-8")
            self.assertIn(plain + kept + "  throws: [typeerror]\n", text)


if __name__ == "__main__":
    unittest.main()
