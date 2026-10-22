"""Tests for compile_facts.py: the closure check over php-src's call compiler.

Run: python3 -I tools/test_compile_facts.py (from the repository root, with PHP_SRC set to a php-8.5.11
checkout for the tests that read the real compiler).
- frameless counts follow find_frameless_function_info
- an unknown dispatch target, an unresolved ZSTR_KNOWN name and a changed digest each fail the run
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import compile_facts
import php_src

COMPILER = """
static zend_result zend_compile_func_strlen(znode *result, zend_ast_list *args)
{
	zend_compile_expr(&n, args->child[0]);
	return SUCCESS;
}
static zend_result zend_compile_func_array_key_exists(znode *result, zend_ast_list *args)
{
	if (args->children != 2) { return FAILURE; }
	zend_compile_expr(&a, args->child[0]);
	zend_compile_expr(&b, args->child[1]);
	return SUCCESS;
}
static zend_result zend_try_compile_special_func_ex(znode *result, zend_string *lcname, zend_ast_list *args)
{
	if (zend_string_equals_literal(lcname, "strlen")) {
		return zend_compile_func_strlen(result, args);
	} else if (zend_string_equals(lcname, ZSTR_KNOWN(ZEND_STR_COUNT))) {
		return zend_compile_func_array_key_exists(result, args);
	} else {
		return FAILURE;
	}
}
"""
STRINGS = '\t_(ZEND_STR_COUNT,                  "count") \\\n'


class ClosureCheck(unittest.TestCase):
    def read(self, compiler=COMPILER, strings=STRINGS, pinned=True):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "Zend").mkdir()
            (Path(root) / compile_facts.COMPILER).write_text(compiler)
            (Path(root) / compile_facts.STRINGS).write_text(strings)
            text = php_src.strip_comments(compiler, "t")
            digests = {}
            if pinned:
                for name in ("zend_compile_func_strlen", "zend_compile_func_array_key_exists", compile_facts.DISPATCH_FUNCTION):
                    digests[name] = compile_facts.digest(compile_facts.function_text(text, name))
            return compile_facts.read_compiler(Path(root), digests, pins=tuple(digests))

    def test_resolves_a_known_string_and_reads_the_special_count(self):
        self.assertEqual({"count": 2}, self.read().special)

    def test_unknown_target_fails(self):
        source = COMPILER.replace("zend_compile_func_strlen(result", "zend_compile_func_mystery(result")
        source += "static zend_result zend_compile_func_mystery(znode *r, zend_ast_list *args)\n{\n}\n"
        with self.assertRaisesRegex(php_src.ExtractionFailure, "no disposition"):
            self.read(source, pinned=False)

    def test_unresolved_known_string_fails(self):
        with self.assertRaisesRegex(php_src.ExtractionFailure, "ZEND_STR_COUNT"):
            self.read(strings="")

    def test_changed_digest_fails(self):
        changed = COMPILER.replace("zend_compile_expr(&n, args->child[0]);", "zend_compile_expr(&n, args->child[0]); n++;")
        with self.assertRaisesRegex(php_src.ExtractionFailure, "changed or unpinned"):
            self.read_with_digests_of(COMPILER, changed)

    def read_with_digests_of(self, pinned_source, actual_source):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "Zend").mkdir()
            (Path(root) / compile_facts.COMPILER).write_text(actual_source)
            (Path(root) / compile_facts.STRINGS).write_text(STRINGS)
            text = php_src.strip_comments(pinned_source, "t")
            names = ("zend_compile_func_strlen", "zend_compile_func_array_key_exists", compile_facts.DISPATCH_FUNCTION)
            digests = {n: compile_facts.digest(compile_facts.function_text(text, n)) for n in names}
            compile_facts.read_compiler(Path(root), digests, pins=names)


class FramelessSelection(unittest.TestCase):
    def test_counts_follow_the_first_matching_tag(self):
        self.assertEqual({2, 3}, compile_facts.frameless_counts([2, 3], 2, False))
        self.assertEqual({1, 2}, compile_facts.frameless_counts([1, 2], 1, False))
        self.assertEqual(set(), compile_facts.frameless_counts([], 1, False))

    def test_variadic_requires_an_equal_arity(self):
        self.assertEqual({2}, compile_facts.frameless_counts([2], 1, True))
        self.assertEqual({1, 2}, compile_facts.frameless_counts([1, 2], 1, True))


@unittest.skipUnless(os.environ.get("PHP_SRC"), "PHP_SRC names a php-8.5.11 checkout")
class RealCompiler(unittest.TestCase):
    def test_pinned_digests_match(self):
        facts = compile_facts.read_compiler(Path(os.environ["PHP_SRC"]))
        self.assertEqual({"array_key_exists": 2}, facts.special)
        self.assertEqual({"sprintf": 0}, facts.rope)


if __name__ == "__main__":
    unittest.main()
