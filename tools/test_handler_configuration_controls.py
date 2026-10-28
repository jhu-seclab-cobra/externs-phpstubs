"""Exhaustive source groups with the same lexical declaration.

- test_equal_bindings_complete: seven equal branch bindings finish within the existing visit bound
- test_equal_bindings_handler: the same groups retain their established numeric handler summary
- test_equal_bindings_inline: statement expressions share exhaustive binding normalization
- test_equal_bindings_retry: a suspended call retains the equal-binding callee's result
- test_equal_bindings_values: one binding retains every branch's initializer value
- test_equal_bindings_elif: all three exhaustive branches use the same local
- test_optional_bindings_elif: equal explicit branches retain the missing-else enclosing alternative
- test_signature_equal_bindings: the signature adapter supplies source exhaustiveness
- test_signature_equal_bindings_inline: the signature adapter retains source context in statement expressions
"""

import tempfile
import unittest
from pathlib import Path

import fixture_handler_tree
from handler_memory import Fn, State, alternatives
from handler_minit import Registered
from handler_summary import SummaryPolicy, Summarizer
from named_extras_flow import FlowIndex, FlowMachine
from php_src_c import Program

SOURCE = Path("ext/demo/configuration_controls.c")
FIXTURE = Path(__file__).parent / "testdata/lexical_scopes/configuration_controls.c"


class ConfigurationControlsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name)
        source = "\n".join(path.read_text(encoding="utf-8") for path in
                           (FIXTURE, FIXTURE.with_name("configuration_binding_sites.c")))
        fixture_handler_tree.write_tree(root, {SOURCE.as_posix(): source})
        cls.registered = Registered(Program(root, provenance=True))

    def test_equal_bindings_complete(self) -> None:
        machine = self.registered.machine
        machine.policy = SummaryPolicy()
        definition = self.registered.program.functions["check2_same_binding"][0]
        exits, complete = machine.call(definition, [], State(self.registered.world), 10000)
        values = {value for result, _ in exits for value, _ in alternatives(result)}
        self.assertEqual((True, {13}), (complete, values))

    def test_equal_bindings_handler(self) -> None:
        result = Summarizer(self.registered).cast(Fn("check2_cast_same_binding", SOURCE), "IS_LONG", False)
        self.assertEqual(frozenset({"num"}), result.results)

    def values(self, name: str) -> set[int]:
        machine = self.registered.machine
        machine.policy = SummaryPolicy()
        definition = self.registered.program.functions["check2_" + name][0]
        exits, complete = machine.call(definition, [], State(self.registered.world), 10000)
        self.assertTrue(complete)
        return {value for result, _ in exits for value, _ in alternatives(result)}

    def test_equal_bindings_inline(self) -> None:
        self.assertEqual({13}, self.values("inline_same_binding"))

    def test_equal_bindings_retry(self) -> None:
        result = Summarizer(self.registered).cast(Fn("check2_cast_inline_same_binding", SOURCE), "IS_LONG", False)
        self.assertEqual(frozenset({"num"}), result.results)

    def test_equal_bindings_values(self) -> None:
        self.assertEqual({5, 7}, self.values("same_binding_values"))

    def test_equal_bindings_elif(self) -> None:
        self.assertEqual({5, 7, 11}, self.values("same_binding_elif"))

    def test_optional_bindings_elif(self) -> None:
        self.assertEqual({5, 13}, self.values("optional_binding_elif"))

    def flow_values(self, name: str) -> tuple[bool, set[int]]:
        program = self.registered.program
        machine = FlowMachine(FlowIndex(program))
        exits, complete = machine.call(program.functions[name][0], [], State(self.registered.world), 10000)
        return complete, {value for result, _ in exits for value, _ in alternatives(result)}

    def test_signature_equal_bindings(self) -> None:
        self.assertEqual((True, {13}), self.flow_values("check2_same_binding"))

    def test_signature_equal_bindings_inline(self) -> None:
        self.assertEqual((True, {13}), self.flow_values("check2_inline_same_binding"))
