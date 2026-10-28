"""Tests for php_src.Entry.with_signature: the field-preserving signature writer (design-extraction-handlers.md).

Run: python3 -B -m unittest discover -s tools -p "test_*.py" (from the externs-phpstubs root).
- owned keys are replaced in place, recomputed from the new block, and removed when the block omits them
- a missing signature is inserted after the subject lines
- unowned fields keep their bytes: nested values, comments, blank lines, the sections after the signature, EOF
- adjacent entries and the document bytes outside the rewritten entries stay as they are
- relocation and rewrite leave the hand-declared directories and the set documents untouched, byte for byte
- an entry the transform does not name (an external class) keeps every byte; an old generated value is not evidence
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import php_src

OWNED = ("classifier", "parent", "interfaces", "isFinal", "handlers")
HEADER = "# Generated from php-src stubs by tools/extract_hierarchy.py.\n# Do not hand-edit.\n"


def block(*lines):
    return "  signature:\n" + "".join(f"    {line}\n" for line in lines)


def only(text):
    (entry,) = php_src.entries(text)
    return entry


def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class OwnedFieldsTest(unittest.TestCase):
    def test_owned_keys_are_replaced_in_place(self):
        entry = only("- subject:\n    class: a\n" + block("classifier: class", "parent: old", "interfaces: [x]"))
        updated = entry.with_signature(block("classifier: class", "parent: new", "isFinal: true"), OWNED)
        self.assertEqual("- subject:\n    class: a\n" + block("classifier: class", "parent: new", "isFinal: true"), updated)

    def test_owned_key_absent_from_the_block_is_removed(self):
        old = block("classifier: class", "isFinal: true", "handlers:", "  - id: a.c:t", "    facts: []")
        updated = only("- subject:\n    class: a\n" + old).with_signature(block("classifier: class"), OWNED)
        self.assertEqual("- subject:\n    class: a\n" + block("classifier: class"), updated)

    def test_nested_owned_value_is_replaced_whole(self):
        old = block("classifier: class", "handlers:", "  - id: a.c:t", "    facts:", "      - slot: compare", "  trailer: 1")
        updated = only("- subject:\n    class: a\n" + old).with_signature(
            block("classifier: class", "handlers:", "  - id: b.c:u", "    facts: []"), OWNED
        )
        self.assertEqual(
            "- subject:\n    class: a\n" + block("classifier: class", "handlers:", "  - id: b.c:u", "    facts: []"), updated
        )

    def test_new_owned_key_is_inserted_after_its_predecessor(self):
        old = block("classifier: class", "returnType: void", "parent: p")
        updated = only("- subject:\n    class: a\n" + old).with_signature(
            block("classifier: class", "parent: p", "isFinal: false"), OWNED
        )
        self.assertEqual(
            "- subject:\n    class: a\n" + block("classifier: class", "returnType: void", "parent: p", "isFinal: false"), updated
        )

    def test_first_owned_key_with_no_predecessor_leads_the_signature(self):
        updated = only("- subject:\n    class: a\n" + block("returnType: void")).with_signature(block("classifier: class"), OWNED)
        self.assertEqual("- subject:\n    class: a\n" + block("classifier: class", "returnType: void"), updated)

    def test_block_key_outside_the_owned_fields_is_rejected(self):
        with self.assertRaises(ValueError):
            only("- subject:\n    class: a\n" + block("classifier: class")).with_signature(block("returnType: void"), OWNED)


class UnownedFieldsTest(unittest.TestCase):
    TEXT = (
        "- subject:\n    class: a\n"
        "  signature:\n"
        "    classifier: class\n"
        "    # kept comment\n"
        "    final_note:\n"
        "      - first: 1\n"
        "        second: [a, b]\n"
        "\n"
        "      - first: 2\n"
        "    isFinal: true\n"
        "\n"
        "  throws: [typeerror]\n"
        "  extra:\n    key: value\n"
    )

    def test_unowned_nested_values_comments_and_blank_lines_survive(self):
        updated = only(self.TEXT).with_signature(block("classifier: class", "isFinal: false"), OWNED)
        self.assertEqual(self.TEXT.replace("isFinal: true", "isFinal: false"), updated)

    def test_sections_after_the_signature_survive_when_the_signature_changes(self):
        updated = only(self.TEXT).with_signature(block("classifier: interface"), OWNED)
        self.assertTrue(updated.endswith("\n  throws: [typeerror]\n  extra:\n    key: value\n"))
        self.assertIn("    classifier: interface\n    # kept comment\n    final_note:\n", updated)
        self.assertNotIn("isFinal", updated)

    def test_rewriting_with_the_same_block_is_the_identity(self):
        entry = only(self.TEXT)
        same = entry.with_signature(block("classifier: class", "isFinal: true"), OWNED)
        self.assertEqual(self.TEXT, same)
        self.assertEqual(self.TEXT, only(same).with_signature(block("classifier: class", "isFinal: true"), OWNED))

    def test_signature_missing_is_inserted_after_the_subject(self):
        text = "- subject:\n    class: a\n  throws: [x]\n"
        updated = only(text).with_signature(block("classifier: class"), OWNED)
        self.assertEqual("- subject:\n    class: a\n" + block("classifier: class") + "  throws: [x]\n", updated)

    def test_signature_missing_at_end_of_file(self):
        updated = only("- subject:\n    class: a\n").with_signature(block("classifier: class"), OWNED)
        self.assertEqual("- subject:\n    class: a\n" + block("classifier: class"), updated)

    def test_end_of_file_without_newline_is_kept(self):
        text = "- subject:\n    class: a\n  signature:\n    classifier: class\n    isFinal: true"
        kept = only(text).with_signature(block("classifier: class", "isFinal: true"), OWNED)
        self.assertEqual(text, kept)
        replaced = only(text).with_signature(block("classifier: class", "isFinal: false"), OWNED)
        self.assertEqual(text.replace("true", "false"), replaced)
        appended = only("- subject:\n    class: a\n  signature:\n    returnType: void").with_signature(
            block("classifier: class"), OWNED
        )
        self.assertEqual("- subject:\n    class: a\n  signature:\n    classifier: class\n    returnType: void", appended)


class DocumentTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_adjacent_entries_rewrite_independently(self):
        text = (
            HEADER
            + "- subject:\n    class: a\n"
            + block("classifier: class", "isFinal: true")
            + "- subject:\n    class: b\n"
            + block("classifier: class", "note: keep")
            + "- subject:\n    function: f\n  signature:\n    returnType: void\n"
        )
        write(self.root, "core.yaml", text)

        def transform(entry):
            if entry.kind != "class":
                return entry.text
            return entry.with_signature(block("classifier: class", "isFinal: false"), OWNED)

        self.assertEqual(1, php_src.rewrite(self.root, transform))
        updated = (self.root / "core.yaml").read_text(encoding="utf-8")
        expected = (
            HEADER
            + "- subject:\n    class: a\n"
            + block("classifier: class", "isFinal: false")
            + "- subject:\n    class: b\n"
            + block("classifier: class", "isFinal: false", "note: keep")
            + "- subject:\n    function: f\n  signature:\n    returnType: void\n"
        )
        self.assertEqual(expected, updated)
        self.assertTrue(updated.startswith(HEADER))
        self.assertIn("function: f\n  signature:\n    returnType: void\n", updated)

    def test_hand_declared_documents_and_set_documents_stay(self):
        entry = "- subject:\n    class: a\n" + block("classifier: class", "isFinal: true")
        write(self.root, "core.yaml", HEADER + entry)
        write(self.root, "language/core.yaml", entry)
        write(self.root, "manual/core.yaml", entry)
        write(self.root, "provenance.yaml", entry)

        def transform(item):
            return item.with_signature(block("classifier: class"), OWNED)

        self.assertEqual(1, php_src.rewrite(self.root, transform))
        for name in ("language/core.yaml", "manual/core.yaml", "provenance.yaml"):
            self.assertEqual(entry, (self.root / name).read_text(encoding="utf-8"))

    def test_relocation_leaves_hand_declared_and_set_documents_byte_for_byte(self):
        entry = "- subject:\n    class: a\n" + block("classifier: class", "note: keep") + "  # manual\n"
        for name in ("language/core.yaml", "manual/core.yaml", "provenance.yaml"):
            write(self.root, name, entry)
        write(self.root, "core.yaml", HEADER + entry)

        self.assertEqual(1, php_src.relocate(self.root, {("class", "a"): "spl"}, "tools/test.py"))
        for name in ("language/core.yaml", "manual/core.yaml", "provenance.yaml"):
            self.assertEqual(entry, (self.root / name).read_text(encoding="utf-8"))

    def test_entry_the_transform_leaves_alone_keeps_every_byte_and_is_not_counted(self):
        external = "- subject:\n    class: redis\n" + block("classifier: class") + "  # external\n\n"
        generated = "- subject:\n    class: a\n" + block("classifier: class", "isFinal: true")
        write(self.root, "core.yaml", HEADER + external + generated)

        def transform(item):
            return item.with_signature(block("classifier: class"), OWNED) if item.key() == ("class", "a") else item.text

        self.assertEqual(1, php_src.rewrite(self.root, transform))
        self.assertEqual(HEADER + external + "- subject:\n    class: a\n" + block("classifier: class"),
                         (self.root / "core.yaml").read_text(encoding="utf-8"))

    def test_old_generated_handler_value_is_recomputed_and_never_preserved(self):
        stale = "- subject:\n    class: a\n" + block("classifier: class", "handlers:\n      - id: old")
        write(self.root, "core.yaml", HEADER + stale)
        php_src.rewrite(self.root, lambda item: item.with_signature(block("classifier: class", "isFinal: false"), OWNED))
        text = (self.root / "core.yaml").read_text(encoding="utf-8")
        self.assertNotIn("old", text)
        self.assertIn("isFinal: false", text)

    def test_relocation_moves_entries_with_every_unowned_byte(self):
        moved = "- subject:\n    class: a\n" + block("classifier: class", "note: keep") + "  throws: [x]\n\n  # tail\n"
        stays = "- subject:\n    class: b\n" + block("classifier: class")
        write(self.root, "core.yaml", HEADER + moved + stays)
        count = php_src.relocate(self.root, {("class", "a"): "spl"}, "tools/test.py")
        self.assertEqual(1, count)
        self.assertEqual(HEADER + stays, (self.root / "core.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            "# Generated from php-src stubs by tools/test.py.\n# Do not hand-edit; corrections belong in a higher configuration layer.\n"
            + moved,
            (self.root / "spl.yaml").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
