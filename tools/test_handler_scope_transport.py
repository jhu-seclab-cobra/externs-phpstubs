"""Named transport through the shared compiler, independently of signature admission.

- test_shadowed_collection: the repair note's outer NULL collection never forwards
- test_shadowed_call_info: the repair note's outer cleared fci never forwards
- test_nested_sites: parameter, for, expression and ancestor locals end with their scope
- test_live_and_sibling_locals: every currently valid local transport remains established
- test_declines_remain_conservative: signature admission remains a separate contract
- test_real_shadowed_call_info: the pinned handler variant uses its outer cleared fci
"""

import os
import shutil
import tempfile
import unittest
from copy import copy
from pathlib import Path

from handler_index import Index
from named_extras import definition_policy, read_policies
from named_extras_flow import FlowIndex, FlowMachine, Forwarding, control_flow
from php_src_c import Program

FIXTURES = Path(__file__).parent / "testdata"


class SharedFlowIndex(FlowIndex):
    # Exercise the shared compiler directly; signature admission has its own permanent tests.
    def compile(self, definition):
        return control_flow(Index.compile(self, definition))


def shared_policy(program, definition):
    flow = Forwarding(program)
    flow.machine = FlowMachine(SharedFlowIndex(program))
    return definition_policy(flow, definition)


class SharedTransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name)
        shutil.copytree(FIXTURES / "named_extras_boundaries", root, dirs_exist_ok=True)
        cls.program = Program(root)

    def policy(self, name):
        return shared_policy(self.program, self.program.functions["zif_" + name][0])

    def test_shadowed_collection(self):
        self.assertIsNone(self.policy("check_shadowed_collection"))

    def test_shadowed_call_info(self):
        self.assertIsNone(self.policy("check_shadowed_fci"))

    def test_nested_sites(self):
        for name in ("parameter", "for", "expression", "ancestor", "outer_reference"):
            with self.subTest(site=name):
                self.assertIsNone(self.policy("check_shadowed_" + name))

    def test_live_and_sibling_locals(self):
        for name in ("check_local_forward", "check_sibling_scopes"):
            with self.subTest(site=name):
                self.assertEqual(("forward", None), self.policy(name))

    def test_declines_remain_conservative(self):
        keys = [("function", "check_shadowed_" + site) for site in ("collection", "fci", "parameter", "for", "expression", "ancestor")]
        self.assertEqual(dict.fromkeys(keys), read_policies(self.program, keys))

    @unittest.skipUnless(os.environ.get("PHP_SRC"), "PHP_SRC names the pinned php-src checkout")
    def test_real_shadowed_call_info(self):
        program = Program(Path(os.environ["PHP_SRC"]), provenance=True)
        definition = copy(program.functions["zif_call_user_func"][0])
        fixture = FIXTURES / "named_extras_real_scope/call_user_func.c"
        definition.body = fixture.read_text(encoding="utf-8").removeprefix("PHP_FUNCTION(call_user_func)\n")
        self.assertIsNone(shared_policy(program, definition))
