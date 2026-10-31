"""Tests for extract_hierarchy.py: the class name and class aliases a php-src stub declares.

Run: python3 -I -B tools/test_extract_hierarchy_alias.py (from the externs-phpstubs root, with PHP_SRC set to a php-src
checkout for the tests that read the real stubs).
- a class takes its declared name and the folded value of its @alias tag
- the last alias tag wins; a tag without a value, or with a value that is no class spelling, fails
- a doc comment inside a block comment or an attribute is no doc comment
- two stubs declaring one class with different names or aliases fail
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import extract_hierarchy
import php_src


def declarations(*stubs):
    """The declarations read from php-src stubs, each given as the text of ext/<n>/<n>.stub.php."""
    with tempfile.TemporaryDirectory() as root:
        for number, text in enumerate(stubs):
            path = Path(root, "ext", f"e{number}", f"e{number}.stub.php")
            path.parent.mkdir(parents=True)
            path.write_text("<?php\n" + text, encoding="utf-8")
        return extract_hierarchy.read_php_src(Path(root))


class AliasTag(unittest.TestCase):
    def test_a_class_without_a_tag_has_a_name_and_no_aliases(self):
        found = declarations("namespace Dom;\nclass Plain {}\n")["dom\\plain"]
        self.assertEqual("Dom\\Plain", found.name)
        self.assertEqual([], found.aliases)

    def test_the_value_is_folded_and_loses_one_leading_separator(self):
        found = declarations("/** @alias \\Dom\\DOMException */\nfinal class DOMException {}\n")["domexception"]
        self.assertEqual("DOMException", found.name)
        self.assertEqual(["dom\\domexception"], found.aliases)

    def test_the_one_line_and_the_multi_line_forms_read_alike(self):
        one = declarations("/** @alias A\\B */\nclass C {}\n")["c"]
        many = declarations("/**\n * @alias A\\B\n */\nclass C {}\n")["c"]
        self.assertEqual(one.aliases, many.aliases)
        self.assertEqual(["a\\b"], many.aliases)

    def test_the_last_tag_wins_across_comments(self):
        found = declarations("/** @alias A\\B */\n/** @alias A\\D */\nclass C {}\n")["c"]
        self.assertEqual(["a\\d"], found.aliases)

    def test_an_attribute_between_the_comment_and_the_class_keeps_the_tag(self):
        found = declarations("/** @alias A\\B */\n#[AllowDynamicProperties]\nclass C {}\n")["c"]
        self.assertEqual(["a\\b"], found.aliases)

    def test_a_doc_comment_inside_a_block_comment_is_no_doc_comment(self):
        # PHP 8.5.12: /* /** @alias Ghost */ class C {} class_exists('Ghost') -> bool(false)
        found = declarations("/* /** @alias Ghost */\nclass C {}\n")["c"]
        self.assertEqual([], found.aliases)

    def test_a_doc_comment_inside_an_attribute_is_no_doc_comment(self):
        # PHP 8.5.12: #[SomeAttr(/** @alias Ghost */ 1)] class C {} class_exists('Ghost') -> bool(false)
        found = declarations("#[SomeAttr(/** @alias Ghost */ 1)]\nclass C {}\n")["c"]
        self.assertEqual([], found.aliases)

    def test_a_valueless_tag_inside_an_attribute_neither_fails_nor_aliases(self):
        found = declarations("#[SomeAttr(/** @alias */ 1)]\nclass C {}\n")["c"]
        self.assertEqual([], found.aliases)

    def test_a_tag_before_another_declaration_is_not_read(self):
        found = declarations("/** @alias f2 */\nfunction f() {}\nclass C {}\n")["c"]
        self.assertEqual([], found.aliases)

    def test_a_value_that_is_no_class_spelling_fails(self):
        with self.assertRaises(php_src.ExtractionFailure):
            declarations("/** @alias 1A */\nclass C {}\n")

    def test_a_tag_without_a_value_fails_even_when_a_later_tag_has_one(self):
        with self.assertRaises(php_src.ExtractionFailure):
            declarations("/**\n * @alias\n * @alias A\\B\n */\nclass C {}\n")

    def test_two_stubs_declaring_one_class_with_different_aliases_fail(self):
        with self.assertRaises(php_src.ExtractionFailure):
            declarations("/** @alias A\\B */\nclass C {}\n", "class C {}\n")

    def test_two_stubs_declaring_one_class_with_different_names_fail(self):
        with self.assertRaises(php_src.ExtractionFailure):
            declarations("namespace N;\nclass C {}\n", "namespace n;\nclass c {}\n")


@unittest.skipUnless(os.environ.get("PHP_SRC"), "PHP_SRC names a php-src checkout")
class RealStubs(unittest.TestCase):
    def setUp(self):
        self.found = extract_hierarchy.read_php_src(Path(os.environ["PHP_SRC"]))

    def test_dom_exception_is_registered_under_the_dom_namespace(self):
        found = self.found["domexception"]
        self.assertEqual("DOMException", found.name)
        self.assertEqual(["dom\\domexception"], found.aliases)

    def test_a_namespaced_class_keeps_its_letter_case(self):
        self.assertEqual("Dom\\XMLDocument", self.found["dom\\xmldocument"].name)

    def test_dom_exception_is_the_only_class_alias(self):
        self.assertEqual(["domexception"], [n for n, d in self.found.items() if d.aliases])


if __name__ == "__main__":
    unittest.main()
