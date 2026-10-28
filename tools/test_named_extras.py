"""Builtin named-extra extraction from the pinned php-src through the signature producer.

- test_array_map_rejects_at_first_array_reception: the parsing group begins before the declared variadic tail
- test_call_user_func_forwards: the named arguments reach the callback
- test_closure_call_forwards: method signatures carry the same fact
- test_other_forwarders: Reflection helper and Fiber parsing preserve forwarding
- test_imagefilter_is_unextracted: accept-and-ignore never becomes a rejection
- test_nonvariadic_has_no_fact: ordinary parameters carry no policy
- test_aliases_follow_registered_handlers: alias registration uses the same implementation
- test_post_variadic_argument_keeps_group_start: a required trailing argument does not shift reception
- test_named_parser_must_reach_callable: merely retaining names never asserts forwarding
- test_literal_helper_selects_forwarding_branch: helper argument zero takes the other branch
- test_unknown_patterns_stay_null: incomplete source, control flow and unknown reception stay unextracted
- test_overwritten_named_collection_stays_null: replacing the parsed collection proves no forwarding
- test_unread_parsing_block_stays_null: a recognized block never hides an unread one
- test_changed_primitive_stays_null: changed rejection semantics establish no fact
- test_rendered_policy_survives_regeneration: the fact is emitted in the existing params block
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import extract_signatures
from php_src_c import Program


@unittest.skipUnless(os.environ.get("PHP_SRC"), "PHP_SRC names the pinned php-src checkout")
class RealNamedExtrasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signatures = extract_signatures.read_php_src(Path(os.environ["PHP_SRC"]))

    def policy(self, kind, name):
        signature = self.signatures[(kind, name)]
        return next((p.named_extras for p in signature.params if p.variadic), None)

    def test_array_map_rejects_at_first_array_reception(self):
        self.assertEqual(("reject", 1), self.policy("function", "array_map"))

    def test_call_user_func_forwards(self):
        self.assertEqual(("forward", None), self.policy("function", "call_user_func"))

    def test_closure_call_forwards(self):
        self.assertEqual(("forward", None), self.policy("method", "closure::call"))

    def test_other_forwarders(self):
        for name in ("reflectionfunction::invoke", "reflectionmethod::invoke", "reflectionclass::newinstance", "fiber::start"):
            with self.subTest(name=name):
                self.assertEqual(("forward", None), self.policy("method", name))

    def test_imagefilter_is_unextracted(self):
        self.assertIsNone(self.policy("function", "imagefilter"))

    def test_nonvariadic_has_no_fact(self):
        signature = self.signatures[("function", "strlen")]
        self.assertEqual([None], [p.named_extras for p in signature.params])

    def test_rendered_policy_survives_regeneration(self):
        rendered = self.signatures[("function", "array_map")].render()
        self.assertIn("      namedExtras: {kind: reject, position: 1}\n", rendered)
        self.assertEqual(1, rendered.count("namedExtras:"))


class SourcePatternTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.directory.name)
        shutil.copytree(Path(__file__).parent / "testdata/named_extras", cls.root, dirs_exist_ok=True)
        cls.program = Program(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def policy(self, name):
        import named_extras
        return named_extras.read_policies(self.program, [("function", name)])[("function", name)]

    def test_aliases_follow_registered_handlers(self):
        self.assertEqual(("reject", 2), self.policy("alias"))

    def test_post_variadic_argument_keeps_group_start(self):
        self.assertEqual(("reject", 1), self.policy("reject_ex"))

    def test_named_parser_must_reach_callable(self):
        self.assertEqual(("forward", None), self.policy("forward"))
        self.assertIsNone(self.policy("ignored"))

    def test_literal_helper_selects_forwarding_branch(self):
        self.assertEqual(("forward", None), self.policy("wrapper"))
        self.assertIsNone(self.policy("unselected"))

    def test_unknown_patterns_stay_null(self):
        for name in ("conditional", "unknown", "optional", "missing", "conflict", "recursive", "unregistered", "bypass", "miscount"):
            with self.subTest(name=name):
                self.assertIsNone(self.policy(name))

    def test_overwritten_named_collection_stays_null(self):
        self.assertIsNone(self.policy("reassigned"))

    def test_unread_parsing_block_stays_null(self):
        self.assertIsNone(self.policy("unread_block"))

    def test_changed_primitive_stays_null(self):
        import named_extras
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(self.root, root, dirs_exist_ok=True)
            header = root / "zend_API.h"
            header.write_text(header.read_text(encoding="utf-8").replace("ZPP_ERROR_UNEXPECTED_EXTRA_NAMED", "OTHER_ERROR"), encoding="utf-8")
            self.assertIsNone(named_extras.read_policies(Program(root), [("function", "reject")])[("function", "reject")])


if __name__ == "__main__":
    unittest.main()
