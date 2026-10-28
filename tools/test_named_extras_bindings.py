"""Lexical admission at each declaration's source position.

- test_later_enclosing_declaration_is_not_shadowed: an earlier child sees no later parent local
- test_completed_for_then_declaration_is_not_shadowed: a completed loop cannot see the later local
- test_nonshadowed_body_keeps_forwarding: sequential child and parent declarations preserve transport
- test_completed_for_body_keeps_forwarding: a later local does not overlap a completed loop scope
- test_deep_child_body_keeps_forwarding: every ancestor uses declaration order
- test_siblings_then_declaration_keep_forwarding: sibling locals do not see a later parent binding
- test_existing_binding_boundaries_stay_supported: genuine shadows decline and distinct scopes still forward
- test_later_declarator_is_not_visible_in_earlier_initializer: declarators are bound in source order
- test_prior_declarator_is_visible_in_later_initializer: an earlier declarator remains an ancestor binding
- test_later_local_reference_is_resolved_locally: a later local use does not become an outer reference
- test_outer_reference_after_child_retains_shadow: an unresolved later use still identifies the outer binding
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from named_extras import Policy, read_policies
from named_extras_bindings import shadowed_bindings
from php_src_c import Program
from php_src_c.definitions import parse_body


class DeclarationOrderRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = Path(__file__).parent / "testdata/named_extras_order/boundaries.json"
        cls.cases = json.loads(fixture.read_text(encoding="utf-8"))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name)
        shutil.copyfile(fixture.parent.parent / "named_extras/zend_API.h", root / "zend_API.h")
        functions = [f'PHP_FUNCTION(order_{case["name"]}) {{ {case["body"]} }}\n' for case in cls.cases]
        entries = [f' ZEND_FE(order_{case["name"]}, arginfo_forward)\n' for case in cls.cases]
        (root / "functions.c").write_text("".join(functions), encoding="utf-8")
        (root / "entries_arginfo.h").write_text(
            "static const zend_function_entry functions[] = {\n" + "".join(entries) + " ZEND_FE_END\n};\n", encoding="utf-8")
        cls.policies = read_policies(Program(root), [("function", "order_" + case["name"]) for case in cls.cases])

    def policy(self, name: str) -> Policy:
        return self.policies[("function", "order_" + name)]

    def test_later_enclosing_declaration_is_not_shadowed(self) -> None:
        body = parse_body("{ { int later = 1; } int later = 2; }")
        self.assertEqual(frozenset(), shadowed_bindings(body, frozenset()))

    def test_completed_for_then_declaration_is_not_shadowed(self) -> None:
        body = parse_body("{ for (int later = 0; later < 1; ++later) { } int later = 2; }")
        self.assertEqual(frozenset(), shadowed_bindings(body, frozenset()))

    def test_nonshadowed_body_keeps_forwarding(self) -> None:
        self.assertEqual(("forward", None), self.policy("before_declaration"))

    def test_completed_for_body_keeps_forwarding(self) -> None:
        self.assertEqual(("forward", None), self.policy("for_before_declaration"))

    def test_deep_child_body_keeps_forwarding(self) -> None:
        self.assertEqual(("forward", None), self.policy("nested_before_declaration"))

    def test_siblings_then_declaration_keep_forwarding(self) -> None:
        self.assertEqual(("forward", None), self.policy("siblings_then_declaration"))

    def test_existing_binding_boundaries_stay_supported(self) -> None:
        for case in self.cases:
            if case["name"].endswith("declaration"):
                continue
            with self.subTest(name=case["name"]):
                expected = ("forward", None) if case["forward"] else None
                self.assertEqual(expected, self.policy(case["name"]))

    def test_later_declarator_is_not_visible_in_earlier_initializer(self) -> None:
        body = parse_body("{ int first = ({ int later = 1; later; }), later = 2; }")
        self.assertEqual(frozenset(), shadowed_bindings(body, frozenset()))

    def test_prior_declarator_is_visible_in_later_initializer(self) -> None:
        body = parse_body("{ int prior = 1, next = ({ int prior = 2; prior; }); }")
        self.assertEqual(frozenset({"prior"}), shadowed_bindings(body, frozenset()))

    def test_later_local_reference_is_resolved_locally(self) -> None:
        body = parse_body("{ { int later = 1; } int later = 2; (void)later; }")
        self.assertEqual(frozenset(), shadowed_bindings(body, frozenset()))

    def test_outer_reference_after_child_retains_shadow(self) -> None:
        body = parse_body("{ { int outside = 1; } (void)outside; }")
        self.assertEqual(frozenset({"outside"}), shadowed_bindings(body, frozenset()))
