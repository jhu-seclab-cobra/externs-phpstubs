"""Builtin named-extra extraction from the pinned php-src through the signature producer.

- test_unreachable_forward_call: unreachable calls establish no forwarding
- test_call_info_cleared_by_helper: intervening helper writes invalidate the parsed collection
- test_conditional_reception: a conditional macro establishes no fixed reception count
- test_unknown_counter_write: an unread counter update leaves the reception count unknown
- test_early_return_and_memset_leave_no_forwarding: early return and zeroing do not preserve names
- test_unread_or_false_guard_leaves_no_forwarding: false and unread conditions prove no reachable target
- test_aliasing_helper_invalidates_call_info: interprocedural aliases share the invalidated field
- test_readonly_helper_preserves_named_collection: a read-only helper keeps the parsed value
- test_unbound_callback_reference_is_not_an_invocation: unexecuted callbacks establish nothing
- test_all_counter_assignments_remain_unknown: every assignment operator uses the same unknown effect
- test_named_collection_contents_are_preserved: writes through the collection pointer invalidate forwarding
- test_unexpanded_recursive_macro_remains_unknown: an unexpanded macro establishes no reception count
- test_unread_intervening_call_prevents_forwarding: unread call effects establish no forwarding
- test_helper_argument_reassignment_stays_null: helper branches use the current bound value
- test_unread_control_before_helper_stays_null: unread caller control invalidates its callees
- test_conditional_prologues_stay_null: equally counted conditional prologues are still conditional
- test_counter_macro_arguments_stay_null: writes through substituted macro arguments are unknown
- test_shadowed_c_apis_stay_null: local definitions determine control and target reachability
- test_shadowed_collection_does_not_forward: an inner collection declaration cannot replace the outer NULL
- test_shadowed_call_info_does_not_forward: an inner fci declaration cannot replace the outer call info
- test_real_handler_shadowed_call_info_does_not_forward: a real handler variant retains its cleared outer fci
- test_real_handler_later_declaration_keeps_forwarding: an unrelated later local preserves the real handler transport
- test_nested_scope_bindings_stay_unextracted: parameters, loops, expressions and ancestors preserve the scope boundary
- test_distinct_local_scopes_can_forward: sibling names and an active local do not shadow an enclosing binding
- test_shadowed_outer_reference_does_not_forward: a nested declaration cannot outlive a referenced outer binding
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
from copy import copy
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

    def test_real_handler_shadowed_call_info_does_not_forward(self) -> None:
        import named_extras
        program = Program(Path(os.environ["PHP_SRC"]), provenance=True)
        name = "zif_call_user_func"
        definition = copy(program.functions[name][0])
        fixture = Path(__file__).parent / "testdata/named_extras_real_scope/call_user_func.c"
        definition.body = fixture.read_text(encoding="utf-8").removeprefix("PHP_FUNCTION(call_user_func)\n")
        program.functions[name] = [definition]
        self.assertIsNone(named_extras.read_policies(program, [("function", "call_user_func")])[("function", "call_user_func")])

    def test_real_handler_later_declaration_keeps_forwarding(self) -> None:
        import named_extras
        program = Program(Path(os.environ["PHP_SRC"]), provenance=True)
        name = "zif_call_user_func"
        definition = copy(program.functions[name][0])
        fixture = Path(__file__).parent / "testdata/named_extras_real_scope/call_user_func_no_shadow.c"
        definition.body = fixture.read_text(encoding="utf-8").removeprefix("PHP_FUNCTION(call_user_func)\n")
        program.functions[name] = [definition]
        self.assertEqual(("forward", None), named_extras.read_policies(program, [("function", "call_user_func")])[("function", "call_user_func")])


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


class BoundaryRegressionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import named_extras
        fixture = Path(__file__).parent / "testdata/named_extras_boundaries"
        names = ("unreachable_forward", "clobbered_fci", "conditional_reception", "mutated_counter",
                 "early_success", "zeroed_fci", "unread_guard", "false_guarded", "aliased_fci",
                 "preserved_fci", "unbound_callback", "mutated_collection", "recursive_macro", "unread_intervening_call",
                 "rebound_argument", "unread_before_helper", "unread_inline_before_helper", "conditional_prologues", "counter_argument_write",
                 "shadowed_jump", "shadowed_target", "check_shadowed_collection", "check_shadowed_fci",
                 "check_shadowed_parameter", "check_shadowed_for", "check_shadowed_expression", "check_shadowed_ancestor",
                 "check_sibling_scopes", "check_local_forward", "check_shadowed_outer_reference")
        cls.policies = named_extras.read_policies(
            Program(fixture, provenance=True), [("function", name) for name in names])

    def test_unreachable_forward_call(self) -> None:
        self.assertIsNone(self.policies[("function", "unreachable_forward")])

    def test_call_info_cleared_by_helper(self) -> None:
        self.assertIsNone(self.policies[("function", "clobbered_fci")])

    def test_conditional_reception(self) -> None:
        self.assertIsNone(self.policies[("function", "conditional_reception")])

    def test_unknown_counter_write(self) -> None:
        self.assertIsNone(self.policies[("function", "mutated_counter")])

    def test_early_return_and_memset_leave_no_forwarding(self) -> None:
        for name in ("early_success", "zeroed_fci"):
            with self.subTest(name=name):
                self.assertIsNone(self.policies[("function", name)])

    def test_unread_or_false_guard_leaves_no_forwarding(self) -> None:
        for name in ("unread_guard", "false_guarded"):
            with self.subTest(name=name):
                self.assertIsNone(self.policies[("function", name)])

    def test_aliasing_helper_invalidates_call_info(self) -> None:
        self.assertIsNone(self.policies[("function", "aliased_fci")])

    def test_readonly_helper_preserves_named_collection(self) -> None:
        self.assertEqual(("forward", None), self.policies[("function", "preserved_fci")])

    def test_unbound_callback_reference_is_not_an_invocation(self) -> None:
        self.assertIsNone(self.policies[("function", "unbound_callback")])

    def test_named_collection_contents_are_preserved(self) -> None:
        self.assertIsNone(self.policies[("function", "mutated_collection")])

    def test_unexpanded_recursive_macro_remains_unknown(self) -> None:
        self.assertIsNone(self.policies[("function", "recursive_macro")])

    def test_unread_intervening_call_prevents_forwarding(self) -> None:
        self.assertIsNone(self.policies[("function", "unread_intervening_call")])

    def test_helper_argument_reassignment_stays_null(self) -> None:
        self.assertIsNone(self.policies[("function", "rebound_argument")])

    def test_unread_control_before_helper_stays_null(self) -> None:
        for name in ("unread_before_helper", "unread_inline_before_helper"):
            with self.subTest(name=name):
                self.assertIsNone(self.policies[("function", name)])

    def test_conditional_prologues_stay_null(self) -> None:
        self.assertIsNone(self.policies[("function", "conditional_prologues")])

    def test_counter_macro_arguments_stay_null(self) -> None:
        self.assertIsNone(self.policies[("function", "counter_argument_write")])

    def test_shadowed_c_apis_stay_null(self) -> None:
        for name in ("shadowed_jump", "shadowed_target"):
            with self.subTest(name=name):
                self.assertIsNone(self.policies[("function", name)])

    def test_shadowed_collection_does_not_forward(self) -> None:
        self.assertIsNone(self.policies[("function", "check_shadowed_collection")])

    def test_shadowed_call_info_does_not_forward(self) -> None:
        self.assertIsNone(self.policies[("function", "check_shadowed_fci")])

    def test_nested_scope_bindings_stay_unextracted(self) -> None:
        for name in ("check_shadowed_parameter", "check_shadowed_for", "check_shadowed_expression", "check_shadowed_ancestor"):
            with self.subTest(name=name):
                self.assertIsNone(self.policies[("function", name)])

    def test_distinct_local_scopes_can_forward(self) -> None:
        for name in ("check_sibling_scopes", "check_local_forward"):
            with self.subTest(name=name):
                self.assertEqual(("forward", None), self.policies[("function", name)])

    def test_shadowed_outer_reference_does_not_forward(self) -> None:
        self.assertIsNone(self.policies[("function", "check_shadowed_outer_reference")])

    def test_all_counter_assignments_remain_unknown(self) -> None:
        import named_extras
        fixture = Path(__file__).parent / "testdata/named_extras_boundaries"
        operators = ("=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=")
        for operator in operators:
            with self.subTest(operator=operator), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copytree(fixture, root, dirs_exist_ok=True)
                source = root / "functions.c"
                source.write_text(source.read_text(encoding="utf-8").replace("_i |= 1", f"_i {operator} 1"), encoding="utf-8")
                self.assertIsNone(named_extras.read_policies(Program(root), [("function", "mutated_counter")])[("function", "mutated_counter")])


if __name__ == "__main__":
    unittest.main()
