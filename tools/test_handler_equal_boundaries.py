"""Equal-binding boundaries, preserving both values and source correlations.

- test_values: different initializers survive collapse to one Local
- test_elif_else: exhaustive equal declarations retain all three initializer values
- test_elif_implicit: the enclosing binding survives a missing final else
- test_nested: only the inner exhaustive group's bindings are equal
- test_inline: a separately compiled statement expression receives source context
- test_flow_inline: the signature caller receives the same inline source context
- test_correlation: two reads of one initialized variable remain correlated
- test_flow_correlation: the signature adapter preserves the same value correlation
- test_inline_correlation: separately compiled equal declarations preserve value identity
- test_flow_inline_correlation: the inline signature adapter preserves value correlation
- test_handler: correlated initializers introduce no impossible normal result kind
- test_loop_retry: equal bindings and initialized values survive a callee retry in a loop
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


FIXTURES = Path(__file__).parent / "testdata/lexical_scopes"
SOURCE = Path("ext/demo/equal_boundaries.c")


class EqualBindingBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name)
        source = '\n'.join((FIXTURES / name).read_text(encoding='utf-8')
                           for name in ('conditional.c', 'equal_boundaries.c'))
        fixture_handler_tree.write_tree(root, {SOURCE.as_posix(): source})
        cls.registered = Registered(Program(root, provenance=True))

    def values(self, name: str) -> set[str]:
        machine = self.registered.machine
        machine.policy = SummaryPolicy()
        exits, complete = machine.call(self.registered.program.functions['check3_' + name][0],
                                       [], State(self.registered.world), 10000)
        self.assertTrue(complete)
        values = {repr(value) for result, _ in exits for value, _ in alternatives(result)}
        return values

    def test_values(self) -> None:
        self.assertEqual({'11', '19'}, self.values('values'))

    def test_elif_else(self) -> None:
        self.assertEqual({'11', '19', '23'}, self.values('elif_else'))

    def test_elif_implicit(self) -> None:
        self.assertEqual({'11', '19', '31'}, self.values('elif_implicit'))

    def test_nested(self) -> None:
        self.assertEqual({'11', '19', '31'}, self.values('nested'))

    def test_inline(self) -> None:
        self.assertEqual({'11', '19'}, self.values('inline'))

    def test_flow_inline(self) -> None:
        program = self.registered.program
        machine = FlowMachine(FlowIndex(program))
        exits, complete = machine.call(program.functions['check3_inline'][0],
                                       [], State(self.registered.world), 10000)
        values = {value for result, _ in exits for value, _ in alternatives(result)}
        self.assertEqual((True, {11, 19}), (complete, values))

    def summary(self, name: str) -> frozenset[str] | None:
        result = Summarizer(self.registered).cast(Fn('check3_cast_' + name, SOURCE), 'IS_LONG', False)
        return result.results

    def test_correlation(self) -> None:
        self.assertEqual({'0'}, self.values('correlation'))

    def test_flow_correlation(self) -> None:
        self.assertEqual({0}, self.flow_values('check3_correlation'))

    def test_inline_correlation(self) -> None:
        self.assertEqual({'0'}, self.values('inline_correlation'))

    def flow_values(self, name: str) -> set[int]:
        program = self.registered.program
        machine = FlowMachine(FlowIndex(program))
        exits, complete = machine.call(program.functions[name][0],
                                       [], State(self.registered.world), 10000)
        self.assertTrue(complete)
        return {value for result, _ in exits for value, _ in alternatives(result)}

    def test_flow_inline_correlation(self) -> None:
        self.assertEqual({0}, self.flow_values('check3_inline_correlation'))

    def test_handler(self) -> None:
        self.assertEqual(frozenset({'num'}), self.summary('handler'))

    def test_loop_retry(self) -> None:
        self.assertEqual(frozenset({'num'}), self.summary('loop'))


if __name__ == '__main__':
    unittest.main()
