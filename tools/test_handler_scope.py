"""Shared C lexical identity, lifetime and procedure continuation regressions.

- test_parameter: a completed child restores the parameter
- test_ancestors: each live ancestor retains its own value
- test_source_order: references before a declarator see the enclosing local
- test_declarators: earlier declarators remain visible to later initializers
- test_self_initializer: a declarator hides its ancestor before initialization
- test_for_init: the loop initializer's local ends at loop exit
- test_for_body: body shadowing cannot replace the induction variable
- test_statement_expression: expression exit restores the surrounding binding
- test_nested_expression: nested expression scopes restore each ancestor
- test_break: a break ends the child's lifetime
- test_continue: a continue ends the iteration's child lifetime
- test_goto_out: a jump out restores the parent binding
- test_goto_back: a backward jump does not retain the abandoned child
- test_goto_into: skipping a declaration does not read an enclosing homonym
- test_return: a return reads the live child before releasing locals
- test_switch: fallthrough restores the binding outside a completed case block
- test_siblings: alternative scopes keep distinct locals on both paths
- test_aliases: a pointer retains the hidden ancestor's identity
- test_struct_copy: copies remain snapshots of distinct aggregate locals
- test_memory_copy: memcpy reads the live child and preserves the enclosing aggregate
- test_array: array decay is restored after a scalar homonym
- test_sizeof: type lookup follows the current lexical binding
- test_expired_alias: an escaped pointer cannot read a completed block's storage
- test_configured_declarations: source alternatives share one binding in the same scope
- test_configured_references: source alternatives start with the same enclosing visibility
- test_summary_checkpoint: retries restore bindings and completed side effects
- test_summary_aliases: summary inputs and effects preserve hidden ancestor aliases
- test_summary_cached: settled effects rebind each sibling's own local
- test_summary_loop: declaration retries and continue targets retain loop bindings
- test_summary_recursive: recursive continuations restore all ancestor locals
"""

import tempfile
import unittest
from pathlib import Path

import fixture_handler_tree
from handler_memory import ANYV, Fn, Size, State, alternatives
from handler_machine import join_exits
from handler_minit import Registered
from handler_summary import SummaryPolicy, Summarizer
from php_src_c import Program

FIXTURES = Path(__file__).parent / "testdata/lexical_scopes"
SOURCE = Path("ext/demo/scope.c")


class LexicalScopeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name)
        fixture_handler_tree.write_tree(root)
        (root / SOURCE).write_text("\n".join(
            (FIXTURES / name).read_text(encoding="utf-8") for name in ("expressions.c", "summaries.c")
        ), encoding="utf-8")
        cls.registered = Registered(Program(root, provenance=True))

    def result(self, name, args=()):
        machine = self.registered.machine
        machine.policy = SummaryPolicy()
        definition = self.registered.program.functions["scope_" + name][0]
        exits, complete = machine.call(definition, list(args), State(self.registered.world), 10000)
        self.assertTrue(complete)
        exits = join_exits(exits)
        self.assertEqual(1, len(exits))
        self.assertFalse(any(rid.startswith("l:") for rid in exits[0][1].mem))
        return exits[0][0]

    def summary(self, name):
        return Summarizer(self.registered).cast(Fn("scope_cast_" + name, SOURCE), "IS_LONG", False).results

    def test_parameter(self):
        self.assertEqual(7, self.result("parameter", (7,)))

    def test_ancestors(self):
        self.assertEqual(6, self.result("ancestors"))

    def test_source_order(self):
        self.assertEqual(17, self.result("source_order"))

    def test_declarators(self):
        self.assertEqual(13, self.result("declarators"))

    def test_self_initializer(self):
        self.assertIs(ANYV, self.result("self_initializer"))

    def test_for_init(self):
        self.assertEqual(7, self.result("for_init"))

    def test_for_body(self):
        self.assertEqual(7, self.result("for_body"))

    def test_statement_expression(self):
        self.assertEqual(4, self.result("statement_expression"))

    def test_nested_expression(self):
        self.assertEqual(6, self.result("nested_expression"))

    def test_break(self):
        self.assertEqual(7, self.result("break"))

    def test_continue(self):
        self.assertEqual(7, self.result("continue"))

    def test_goto_out(self):
        self.assertEqual(7, self.result("goto_out"))

    def test_goto_back(self):
        self.assertEqual(3, self.result("goto_back"))

    def test_goto_into(self):
        self.assertIs(ANYV, self.result("goto_into"))

    def test_return(self):
        self.assertEqual(2, self.result("return"))

    def test_switch(self):
        self.assertEqual(9, self.result("switch"))

    def test_siblings(self):
        self.assertEqual([9, 10], [self.result("siblings", (flag,)) for flag in (1, 0)])

    def test_aliases(self):
        self.assertEqual(12, self.result("aliases"))

    def test_struct_copy(self):
        self.assertEqual(6, self.result("struct_copy"))

    def test_memory_copy(self):
        self.assertEqual(12, self.result("memory_copy"))

    def test_array(self):
        self.assertEqual(3, self.result("array"))

    def test_sizeof(self):
        self.assertEqual(Size("int"), self.result("sizeof"))

    def test_expired_alias(self):
        self.assertIs(ANYV, self.result("expired_alias"))

    def test_configured_declarations(self):
        self.assertEqual({2, 3}, {value for value, _ in alternatives(self.result("configured_declarations"))})

    def test_configured_references(self):
        self.assertEqual({7, 10}, {value for value, _ in alternatives(self.result("configured_references"))})

    def test_summary_checkpoint(self):
        self.assertEqual(frozenset({"num"}), self.summary("checkpoint"))

    def test_summary_aliases(self):
        self.assertEqual(frozenset({"num"}), self.summary("aliases"))

    def test_summary_cached(self):
        self.assertEqual(frozenset({"num"}), self.summary("cached"))

    def test_summary_loop(self):
        self.assertEqual(frozenset({"num"}), self.summary("loop"))

    def test_summary_recursive(self):
        self.assertEqual(frozenset({"num"}), self.summary("recursive"))
