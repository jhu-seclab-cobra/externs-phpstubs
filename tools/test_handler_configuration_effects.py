"""Observability of equal lexical declarations across source alternatives.

- test_dependent_reads: an initializer reads an earlier configuration-dependent declaration
- test_later_writes: the complete branch effects determine value correlation
- test_alias_values: later pointer reads observe the initialized local's configuration
- test_constant_expressions: identical constant expressions require no retained configuration
"""

import tempfile
import unittest
from pathlib import Path

import fixture_handler_tree
from handler_memory import State, alternatives
from handler_minit import Registered
from handler_summary import SummaryPolicy
from php_src_c import Program


class ConfigurationEffectsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name)
        fixture = Path(__file__).parent / "testdata/lexical_scopes/configuration_effects.c"
        fixture_handler_tree.write_tree(root, {"ext/demo/effects.c": fixture.read_text(encoding="utf-8")})
        cls.registered = Registered(Program(root, provenance=True))

    def values(self, name: str) -> set[int]:
        machine = self.registered.machine
        machine.policy = SummaryPolicy()
        definition = self.registered.program.functions["check3_" + name][0]
        exits, complete = machine.call(definition, [], State(self.registered.world), 10000)
        self.assertTrue(complete)
        return {value for result, _ in exits for value, _ in alternatives(result)}

    def test_dependent_reads(self) -> None:
        self.assertEqual({0}, self.values("dependent_reads"))

    def test_later_writes(self) -> None:
        self.assertEqual({0}, self.values("later_writes"))

    def test_alias_values(self) -> None:
        self.assertEqual({0}, self.values("alias_values"))

    def test_constant_expressions(self) -> None:
        values = self.values("constant_expressions")
        definition = self.registered.program.functions["check3_constant_expressions"][0]
        code = self.registered.index.code(definition)
        configurations = sum(instruction[0] == "g" and instruction[4] is not None for instruction in code.instrs)
        self.assertEqual(({23}, 0), (values, configurations))
