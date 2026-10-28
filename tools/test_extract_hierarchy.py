"""Tests for extract_hierarchy.py over the small tree of fixture_handler_tree.py plus a stub file.

Run: python3 -B -m unittest discover -s tools -p "test_*.py" (from the externs-phpstubs root).
- test_namespace_imports_and_both_enum_interfaces: PHP imports and both engine enum interface sets
- test_conflicting_stub_parent_fails: incompatible duplicate stub hierarchies reject
- declarations: classifier, parent, modifiers, and whether a class body declares a string-conversion method
- final-class status: from the registration flags only; a stub that declares a class final while its registration
  lacks the flag fails; an unregistered declaration has none
- handler tables: only registered classes have them; interfaces get none
- the command line rewrites the owned fields of generated entries, adds a declaration no document holds, keeps the
  bytes of an entry php-src does not declare, and a second run over its own output changes nothing
- the handler write patterns of php-src (testdata/handlers): registered flags of classes, interfaces and enums, an
  inherited creator rendered as the parent's tables, the five external classes and two unregistered PDO pseudo-classes
  keeping their bytes, an old generated handler value recomputed, and a second run that changes nothing
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

    def test_namespace_imports_and_both_enum_interfaces(self):
        write_tree(self.root, r"""<?php
namespace N;
use Vendor\Base as B;
class Child extends B implements \Iface {}
enum Plain { case A; }
enum Backed: string { case A = 'a'; }
""")
        declarations = extract_hierarchy.read_php_src(self.root)
        self.assertEqual(
            ('vendor\\base', ['iface']), (declarations['n\\child'].parent, declarations['n\\child'].interfaces)
        )
        self.assertEqual(['unitenum'], declarations['n\\plain'].interfaces)
        self.assertEqual(['unitenum', 'backedenum'], declarations['n\\backed'].interfaces)

    def test_conflicting_stub_parent_fails(self):
        (self.root / 'ext/demo/other.stub.php').write_text(
            '<?php class Pair extends Different {}', encoding='utf-8'
        )
        with self.assertRaisesRegex(php_src.ExtractionFailure, 'pair: .*different hierarchies'):
            extract_hierarchy.read_php_src(self.root)

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


EXTERNAL = "".join(
    f"- subject:\n    class: {name}\n  signature:\n    classifier: class\n"
    for name in ("redis", "memcached", "imagick", "imagickdraw", "imagickpixel", "pdo_pgsql_ext", "pdo_sqlite_ext")
)
STALE = """- subject:
    class: rsdl
  signature:
    classifier: class
    isFinal: true
    handlers:
    - id: stale.c:old_handlers
      facts: []
"""


class RealTreeTest(unittest.TestCase):
    """The hierarchy producer over the handler write patterns of php-src."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        self.root, self.models = base / "src", base / "models"
        fixture_handler_tree.write_real_tree(self.root)
        self.models.mkdir()
        (self.models / "real.yaml").write_text(EXTERNAL + STALE, encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def generated(self):
        return extract_hierarchy.generate(self.root)

    def run_tool(self):
        argv, sys.argv = sys.argv, ["extract_hierarchy.py", "--php-src", str(self.root), "--models", str(self.models)]
        try:
            with redirect_stdout(io.StringIO()) as out:
                extract_hierarchy.main()
        finally:
            sys.argv = argv
        return out.getvalue()

    def text(self):
        return (self.models / "real.yaml").read_text(encoding="utf-8")

    def test_final_status_is_the_registered_flag_for_classes_interfaces_and_enums(self):
        finals = self.generated().finals
        self.assertEqual({"rcdata", "rgmp", "rfinal"}, {name for name, final in finals.items() if final})
        self.assertIs(False, finals["rface"])
        self.assertIs(False, finals["renum"])
        self.assertIs(False, finals["rlink"])

    def test_interface_and_enum_carry_their_classifier_and_no_handler_table(self):
        generated = self.generated()
        self.assertEqual("  signature:\n    classifier: interface\n    isFinal: false\n", generated.signature("rface"))
        enum = generated.signature("renum")
        self.assertTrue(enum.startswith("  signature:\n    classifier: enum\n"))
        self.assertIn("    isFinal: false\n", enum)
        self.assertNotIn("handlers:", enum)

    def test_registered_subclass_of_a_class_fixed_creator_renders_the_parent_tables(self):
        generated = self.generated()
        parent = generated.signature("rlink").split("handlers:\n")[1]
        child = generated.signature("rlinkchild").split("handlers:\n")[1]
        self.assertEqual(parent, child)
        self.assertIn("ext/real/real.c:link_handlers", child)

    def test_external_classes_and_pseudo_classes_keep_their_bytes(self):
        self.run_tool()
        self.assertTrue(self.text().startswith(EXTERNAL))

    def test_old_generated_handler_value_is_recomputed_from_source(self):
        self.run_tool()
        text = self.text()
        self.assertNotIn("stale.c:old_handlers", text)
        self.assertIn("    class: rsdl\n  signature:\n    classifier: class\n    isFinal: false\n    handlers:\n", text)

    def test_second_run_changes_nothing(self):
        self.run_tool()
        first = self.text()
        message = self.run_tool()
        self.assertEqual(first, self.text())
        self.assertIn("0 classes moved, 0 classes added, 0 documents rewritten", message)


if __name__ == "__main__":
    unittest.main()
