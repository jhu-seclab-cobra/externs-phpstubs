"""Importer reader tests.

- test_psalm: namespace scope, imports, signatures and endpoint annotations.
- test_neon: named parameters and path kind retain both meanings.
- test_codeql: typed rows, unqualified rejection and any-argument expansion.
- test_union: same facts deduplicate while different kinds survive.
- test_external_sources: non-request sources use the existing external kind.
- test_missing: facts without signatures are rejected.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('import_library', Path(__file__).with_name('import_library.py'))
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)
DATA = Path(__file__).parent / 'testdata' / 'import_library'


class ImportLibraryTest(unittest.TestCase):
    def setUp(self):
        self.store = module.ImportData()
        module.read_psalm(DATA / 'signatures.phpstub', 'fixture', self.store)

    def test_psalm(self):
        signature = self.store.signatures['demo\\query::run'].signature
        self.assertEqual('Vendor\\Thing', signature['returnType'])
        self.assertEqual('?Vendor\\Thing', signature['params'][1]['type'])
        self.assertTrue(signature['params'][2]['variadic'])
        self.assertIn('outside', {key.rsplit('\\', 1)[-1] for key in self.store.signatures})
        self.assertIn('other\\query::run', self.store.signatures)
        self.assertEqual(4, len(self.store.candidates))

    def test_neon(self):
        module.read_neon(DATA / 'config.neon', self.store)
        facts, rejected = module.resolve(self.store)
        self.assertEqual({'pathtrav', 'ssrf', 'sqli', 'cmdi'},
                         {fact.kind for fact in facts if fact.subject == 'demo\\query::run'})
        self.assertEqual(2, sum(row['reason'] == 'unresolved-parameter' for row in rejected))

    def test_codeql(self):
        module.read_codeql(DATA / 'models.model.yml', self.store)
        facts, rejected = module.resolve(self.store)
        self.assertEqual({0, 1, 2}, {fact.position for fact in facts
                                   if fact.subject == 'demo\\query::run' and fact.kind == 'sqli'})
        self.assertTrue(any(row['reason'] == 'no-class' for row in rejected))
        self.assertTrue(any(fact.kind == 'external-input' for fact in facts))

    def test_union(self):
        module.read_psalm(DATA / 'signatures.phpstub', 'second', self.store)
        facts, _ = module.resolve(self.store)
        self.assertEqual(4, len(facts))
        self.assertEqual({'fixture', 'second'}, facts[0].origins)

    def test_external_sources(self):
        self.store.candidates.append(module.Candidate(
            'illuminate\\session\\store::get', 'sources', 'user-input', '', 'psalm-plugin-laravel', 'Store.phpstub'))
        module.normalize_sources(self.store)
        self.assertEqual('external-input', self.store.candidates[-1].kind)

    def test_missing(self):
        module.read_codeql(DATA / 'models.model.yml', self.store)
        self.store.signatures.clear()
        facts, rejected = module.resolve(self.store)
        self.assertFalse(facts)
        self.assertTrue(any(row['reason'] == 'no-signature' for row in rejected))


if __name__ == '__main__':
    unittest.main()
