"""Lexical bindings that vary by source configuration.

- test_first_branch: the first branch's local does not hide the enclosing alternative
- test_last_branch: the last branch's local does not hide the enclosing alternative
- test_missing_else: an implicit alternative retains its enclosing declaration
- test_handler_results: every configuration contributes its normal result kind
- test_subsequent: writes and child scope exit keep the selected binding
- test_alias: addresses and stores refer to the selected lexical region
- test_parameter: the undeclared alternative retains the incoming parameter
- test_array: each configuration keeps its pointer or array interpretation
- test_sizeof: each configuration retains its declared type
- test_global_call: an absent local binding leaves a direct function call
- test_expression: child expressions restore the selected parent binding
- test_correlated: two reads in one instruction use the same configuration
- test_branch_write: a joined enclosing write stays with its own configuration
- test_loop: loop heads retain the selected binding through repeated joins
- test_exit_join: distinct live configurations are not merged before local release
- test_unused_bindings: optional locals used only inside their branches add no later state combinations
- test_type_words: type words and field designators are not variable references
- test_nested: multiple conditional ancestors retain every binding
- test_elif: all explicit alternatives contribute their selected declaration
- test_conditional_retry: suspended expressions restore configuration and side effects
"""

import tempfile
import unittest
from pathlib import Path

import fixture_handler_tree
from handler_machine import Frame, join_exits
from handler_memory import Fn, Size, State, alternatives
from handler_minit import Registered
from handler_summary import SummaryPolicy, Summarizer
from php_src_c import Program

FIXTURES = Path(__file__).parent / "testdata/lexical_scopes"
SOURCE = Path("ext/demo/conditional.c")


class ConditionalScopeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name)
        source = "\n".join((FIXTURES / name).read_text(encoding="utf-8")
                           for name in ("conditional.c", "conditional_sites.c"))
        fixture_handler_tree.write_tree(root, {SOURCE.as_posix(): source})
        cls.registered = Registered(Program(root, provenance=True))

    def values(self, name: str, args: tuple[int, ...] = ()) -> set[int | Size]:
        machine = self.registered.machine
        machine.policy = SummaryPolicy()
        definition = self.registered.program.functions["review_conditional_" + name][0]
        exits, complete = machine.call(definition, list(args), State(self.registered.world), 10000)
        self.assertTrue(complete)
        self.assertFalse(any(rid.startswith("l:") for _, state in exits for rid in state.mem))
        return {value for result, _ in exits for value, _ in alternatives(result)}

    def test_first_branch(self) -> None:
        self.assertEqual({5, 13}, self.values("first"))

    def test_last_branch(self) -> None:
        self.assertEqual({5, 13}, self.values("last"))

    def test_missing_else(self) -> None:
        self.assertEqual({5, 13}, self.values("absent"))

    def test_handler_results(self) -> None:
        result = Summarizer(self.registered).cast(Fn("review_cast_conditional", SOURCE), "IS_LONG", False)
        self.assertEqual(frozenset({"num", "str"}), result.results)

    def test_subsequent(self) -> None:
        self.assertEqual({7, 15}, self.values("subsequent"))

    def test_alias(self) -> None:
        self.assertEqual({7, 15}, self.values("alias"))

    def test_parameter(self) -> None:
        self.assertEqual({5, 13}, self.values("parameter", (13,)))

    def test_array(self) -> None:
        self.assertEqual({5, 13}, self.values("array"))

    def test_sizeof(self) -> None:
        self.assertEqual({Size("char"), Size("long")}, self.values("sizeof"))

    def test_global_call(self) -> None:
        self.assertEqual({5, 13}, self.values("global_call"))

    def test_expression(self) -> None:
        self.assertEqual({10, 26}, self.values("expression"))

    def test_correlated(self) -> None:
        self.assertEqual({0}, self.values("correlated"))

    def test_branch_write(self) -> None:
        self.assertEqual({5, 7}, self.values("branch_write"))

    def test_loop(self) -> None:
        self.assertEqual({5, 13}, self.values("loop"))

    def test_unused_bindings(self) -> None:
        self.assertEqual({13}, self.values("unused"))

    def test_type_words(self) -> None:
        self.assertEqual({5, 13}, self.values("type_words"))

    def test_exit_join(self) -> None:
        machine = self.registered.machine
        machine.policy = SummaryPolicy()
        machine.limit = machine.steps + 10000
        definition = self.registered.program.functions["review_conditional_first"][0]
        frame = Frame(definition, 0)
        exits = machine.execute(frame, self.registered.index.code(definition), State(self.registered.world))
        self.assertEqual(2, len(join_exits(exits)))
        for _, state in exits:
            frame.release(state)

    def test_nested(self) -> None:
        self.assertEqual({5, 7, 13}, self.values("nested"))

    def test_elif(self) -> None:
        self.assertEqual({5, 7, 13}, self.values("elif"))

    def test_conditional_retry(self) -> None:
        result = Summarizer(self.registered).cast(Fn("review_cast_conditional_retry", SOURCE), "IS_LONG", False)
        self.assertEqual(frozenset({"num", "str"}), result.results)
