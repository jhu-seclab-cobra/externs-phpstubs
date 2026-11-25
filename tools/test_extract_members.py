"""Tests for extract_members.py over one stub file.

Run: python3 -B -m unittest discover -s tools -p "test_*.py" (from the externs-phpstubs root).
- typed properties: type, visibility and staticness; an untyped property, a method and an enum case give no entry
- typed class constants: the type of each, including a union, a nullable and a class type; an untyped constant gives none
- names: a class type resolves through the namespace and imports; two constants differing only by case are two members
- conflicting declarations of one member fail
- the command line adds the entries to the document declaring the class, rewrites a generated entry, keeps the bytes
  of an entry php-src does not declare, and a second run over its own output changes nothing; a member of a class no
  generated document declares fails
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import extract_members
import php_src

STUB = """<?php
namespace Demo;
use Lib\\Later;
class Holder
{
    public const string FORMAT = "x";
    final public const int|string FLAG = 1;
    public const ?Later LAST = null;
    public const int Flag = 2;
    public const UNTYPED = 1;
    protected string $file = "";
    public static ?Later $shared = null;
    private readonly int $count;
    public $loose = 0;
    public function method(int $parameter = 0): void {}
    public string $hooked { get => "x"; }
}
enum Level: string
{
    case Low = 'low';
    const int WIDTH = 3;
}
"""

MODELS = """# Generated from php-src stubs by tools/extract_signatures.py.
# Do not hand-edit; corrections belong in a higher configuration layer.
- subject:
    class: demo\\holder
  signature:
    classifier: class
- subject:
    class: demo\\level
  signature:
    classifier: enum
- subject:
    property: Demo\\Holder::$file
  signature:
    type: mixed
    visibility: public
- subject:
    property: Demo\\Holder::$foreign
  signature:
    type: int
    visibility: public
"""


def write_stub(root, text=STUB):
    path = root / "ext/demo/demo.stub.php"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ReadTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        write_stub(self.root)
        self.members = {member.subject: member for member in extract_members.read_php_src(self.root).values()}

    def tearDown(self):
        self.directory.cleanup()

    def test_typed_properties_carry_type_visibility_and_staticness(self):
        file, shared, count = (self.members[f"Demo\\Holder::${name}"] for name in ("file", "shared", "count"))
        self.assertEqual(("string", "protected", False), (file.type, file.visibility, file.static))
        self.assertEqual(("?Lib\\Later", "public", True), (shared.type, shared.visibility, shared.static))
        self.assertEqual(("int", "private", False), (count.type, count.visibility, count.static))

    def test_hooked_property_reads_its_type(self):
        self.assertEqual("string", self.members["Demo\\Holder::$hooked"].type)

    def test_untyped_declarations_methods_and_cases_give_no_member(self):
        self.assertEqual(
            {
                "Demo\\Holder::FORMAT", "Demo\\Holder::FLAG", "Demo\\Holder::LAST", "Demo\\Holder::Flag",
                "Demo\\Holder::$file", "Demo\\Holder::$shared", "Demo\\Holder::$count", "Demo\\Holder::$hooked",
                "Demo\\Level::WIDTH",
            },
            set(self.members),
        )

    def test_class_constants_carry_their_declared_type(self):
        self.assertEqual("string", self.members["Demo\\Holder::FORMAT"].type)
        self.assertEqual("int|string", self.members["Demo\\Holder::FLAG"].type)
        self.assertEqual("?Lib\\Later", self.members["Demo\\Holder::LAST"].type)
        self.assertEqual("int", self.members["Demo\\Level::WIDTH"].type)

    def test_constants_differing_only_by_case_are_two_members(self):
        self.assertIn("Demo\\Holder::FLAG", self.members)
        self.assertIn("Demo\\Holder::Flag", self.members)

    def test_conflicting_declarations_of_one_member_fail(self):
        (self.root / "ext/demo/other.stub.php").write_text(
            "<?php namespace Demo; class Holder { protected int $file; }", encoding="utf-8"
        )
        with self.assertRaisesRegex(php_src.ExtractionFailure, r"Holder::\$file: .* declare different types"):
            extract_members.read_php_src(self.root)


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        self.root, self.models = base / "src", base / "models"
        write_stub(self.root)
        self.models.mkdir()
        (self.models / "demo.yaml").write_text(MODELS, encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def run_tool(self):
        argv, sys.argv = sys.argv, ["extract_members.py", "--php-src", str(self.root), "--models", str(self.models)]
        try:
            with redirect_stdout(io.StringIO()) as out:
                extract_members.main()
        finally:
            sys.argv = argv
        return out.getvalue()

    def text(self):
        return (self.models / "demo.yaml").read_text(encoding="utf-8")

    def test_new_entries_join_the_document_declaring_the_class(self):
        self.run_tool()
        self.assertIn("    class_constant: Demo\\Holder::FORMAT\n  signature:\n    type: string\n", self.text())
        self.assertIn(
            "    property: Demo\\Holder::$shared\n  signature:\n    type: ?Lib\\Later\n    visibility: public\n    static: true\n",
            self.text(),
        )

    def test_generated_entry_is_rewritten_and_a_foreign_one_kept(self):
        self.run_tool()
        self.assertIn(
            "    property: Demo\\Holder::$file\n  signature:\n    type: string\n    visibility: protected\n", self.text()
        )
        self.assertIn("    property: Demo\\Holder::$foreign\n  signature:\n    type: int\n    visibility: public\n", self.text())

    def test_member_of_a_class_no_document_declares_fails(self):
        (self.models / "demo.yaml").write_text(MODELS.split("- subject:\n    class: demo\\level")[0], encoding="utf-8")
        with self.assertRaisesRegex(php_src.ExtractionFailure, "no generated document declares class demo.level"):
            extract_members.add_missing(self.models, extract_members.read_php_src(self.root))

    def test_second_run_changes_nothing(self):
        self.run_tool()
        first = self.text()
        message = self.run_tool()
        self.assertEqual(first, self.text())
        self.assertIn("0 entries added, 0 documents rewritten", message)


if __name__ == "__main__":
    unittest.main()
