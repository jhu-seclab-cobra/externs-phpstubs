"""Tests for extract_hierarchy.py over the small tree of fixture_handler_tree.py plus a stub file.

Run: python3 -B -m unittest discover -s tools -p "test_*.py" (from the externs-phpstubs root).
- declarations: classifier, parent, modifiers, and whether a class body declares a string-conversion method
- final-class status: from the registration flags only; a stub that declares a class final while its registration
  lacks the flag fails; an unregistered declaration has none
- handler tables: only registered classes have them; interfaces get none
- the command line rewrites the owned fields of generated entries, adds a declaration no document holds, keeps the
  bytes of an entry php-src does not declare, and a second run over its own output changes nothing
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import extract_hierarchy
import fixture_handler_tree
import php_src
from php_src_c import Program

STUB = """<?php
interface Marker {}
class Plain {}
final class Counter {}
class Pair extends Plain {}
abstract class Shape {}
class Viamethod
{
    public function __toString(): string {}
}
class Methodfirst
{
    public function __toString(): string {}
}
class Nativefirst
{
    public function __toString(): string {}
}
class Optional {}
class Zeroed {}
class Ghost extends Plain {}
"""

MODELS = """# Generated from php-src stubs by tools/extract_hierarchy.py.
# Do not hand-edit; corrections belong in a higher configuration layer.
- subject:
    class: counter
  signature:
    classifier: class
    isFinal: false
    note: kept
  throws: [stale]
- subject:
    class: pair
  signature:
    classifier: class
- subject:
    class: redis
  signature:
    classifier: class
"""


def write_tree(root, stub=STUB):
    fixture_handler_tree.write_tree(root, {"ext/demo/demo.stub.php": stub})


class HierarchyTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        write_tree(self.root)

    def tearDown(self):
        self.directory.cleanup()

    def generated(self):
        return extract_hierarchy.generate(self.root)

    def test_declaration_records_classifier_parent_and_modifiers(self):
        found = extract_hierarchy.read_php_src(self.root)
        self.assertEqual(("class", "plain"), (found["pair"].classifier, found["pair"].parent))
        self.assertTrue(found["counter"].final)
        self.assertFalse(found["shape"].final)
        self.assertEqual("interface", found["marker"].classifier)

    def test_string_method_is_found_in_the_body_of_the_declaring_class_only(self):
        found = extract_hierarchy.read_php_src(self.root)
        self.assertTrue(found["viamethod"].to_string)
        self.assertFalse(found["optional"].to_string)
        self.assertFalse(found["ghost"].to_string)

    def test_final_status_comes_from_the_registration_flags(self):
        finals = self.generated().finals
        self.assertIs(True, finals["counter"])
        self.assertIs(False, finals["pair"])

    def test_declaration_without_a_registration_has_no_final_status(self):
        finals = self.generated().finals
        self.assertNotIn("ghost", finals)
        self.assertNotIn("marker", finals)

    def test_stub_final_without_the_registration_flag_fails(self):
        write_tree(self.root, STUB.replace("class Pair extends Plain {}", "final class Pair extends Plain {}"))
        with self.assertRaisesRegex(php_src.ExtractionFailure, "pair: .* declares it final"):
            self.generated()

    def test_only_registered_classes_have_handler_tables(self):
        handlers = self.generated().handlers
        self.assertEqual(
            {"plain", "counter", "pair", "viamethod", "methodfirst", "nativefirst", "optional", "zeroed"}, set(handlers)
        )

    def test_signature_renders_final_status_then_the_handler_tables(self):
        text = self.generated().signature("counter")
        self.assertTrue(text.startswith("  signature:\n    classifier: class\n    isFinal: true\n    handlers:\n"))
        self.assertIn("      - id: ext/demo/demo.c:counter_handlers\n", text)

    def test_signature_of_an_unregistered_declaration_has_only_its_hierarchy(self):
        self.assertEqual("  signature:\n    classifier: class\n    parent: plain\n", self.generated().signature("ghost"))


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        self.root, self.models = base / "src", base / "models"
        write_tree(self.root)
        self.models.mkdir()
        (self.models / "demo.yaml").write_text(MODELS, encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def run_tool(self):
        argv, sys.argv = sys.argv, ["extract_hierarchy.py", "--php-src", str(self.root), "--models", str(self.models)]
        try:
            with redirect_stdout(io.StringIO()) as out:
                extract_hierarchy.main()
        finally:
            sys.argv = argv
        return out.getvalue()

    def text(self):
        return (self.models / "demo.yaml").read_text(encoding="utf-8")

    def test_owned_fields_are_rewritten_and_the_rest_kept(self):
        self.run_tool()
        entry = self.text().split("- subject:\n    class: pair\n")[0]
        self.assertIn("    isFinal: true\n    handlers:\n", entry)
        self.assertIn("    note: kept\n", entry)
        self.assertIn("  throws: [stale]\n", entry)

    def test_declaration_no_document_holds_is_added(self):
        self.run_tool()
        self.assertIn("- subject:\n    class: ghost\n  signature:\n    classifier: class\n    parent: plain\n", self.text())
        self.assertIn("class: marker\n  signature:\n    classifier: interface\n", self.text())

    def test_entry_php_src_does_not_declare_keeps_its_bytes(self):
        self.run_tool()
        self.assertIn("    class: redis\n  signature:\n    classifier: class\n- subject:", self.text())

    def test_second_run_changes_nothing(self):
        self.run_tool()
        first = self.text()
        message = self.run_tool()
        self.assertEqual(first, self.text())
        self.assertIn("0 classes added, 0 documents rewritten", message)

    def test_report_counts_the_classes_with_handler_tables(self):
        self.assertIn("8 classes with handler tables", self.run_tool())


if __name__ == "__main__":
    unittest.main()
