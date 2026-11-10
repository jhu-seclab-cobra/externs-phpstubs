"""Importer reader tests.

- test_psalm: namespace scope, imports, signatures and endpoint annotations.
- test_neon: named parameters and path kind retain both meanings.
- test_codeql: typed rows, unqualified rejection and any-argument expansion.
- test_union: same facts deduplicate while different kinds survive.
- test_external_sources: non-request sources use the existing external kind.
- test_missing: facts without signatures are rejected.
- test_hierarchy: native edges, nested traits and inherited endpoint declarations.
- test_intersection: intersection separators remain types, distinct from references.
- test_constant_key: constant-key checks are rejected before declaration lookup.
- test_trait_aliases_and_overrides: aliases retain sources while direct methods override traits.
- test_missing_hierarchy: missing parents and cyclic edges reject endpoints without signatures.
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

    def test_hierarchy(self):
        module.read_psalm(DATA / 'hierarchy.phpstub', 'fixture', self.store)
        module.expand_trait_members(self.store)
        signature = self.store.signatures['demo\\child'].signature
        self.assertEqual('Vendor\\Base', signature['parent'])
        self.assertEqual(['Vendor\\Contract', 'Countable'], signature['interfaces'])
        self.assertEqual(['Vendor\\Contract', 'Countable'], self.store.signatures['demo\\extended'].signature['interfaces'])
        for name in ('inherited', 'execute'):
            self.store.candidates.append(module.Candidate(
                'demo\\child::' + name, 'sinks', 'sqli', 'sql', 'fixture', 'hierarchy.phpstub'))
        facts, rejected = module.resolve(self.store)
        self.assertFalse(rejected)
        self.assertEqual({'input', 'query', 'inherited', 'execute'},
                         {fact.subject.split('::')[1] for fact in facts if fact.subject.startswith('demo\\child::')})
        self.assertIn('vendor\\input', self.store.signatures)
        self.assertIn('vendor\\nested', self.store.signatures)

    def test_intersection(self):
        module.read_psalm(DATA / 'intersection.phpstub', 'fixture', self.store)
        signature = self.store.signatures['demo\\intersection::run'].signature
        self.assertEqual('Vendor\\Thing&Countable', signature['returnType'])
        self.assertEqual(['Vendor\\Thing&Countable', 'Vendor\\Thing&Countable', '(Vendor\\Thing&Countable)|null'],
                         [param['type'] for param in signature['params']])
        self.assertNotIn('byRef', signature['params'][0])
        self.assertTrue(signature['params'][1]['byRef'])

    def test_constant_key(self):
        module.codeql_row(['function', 'openssl_encrypt', 2, 'hardcoded-crypto-key'], ('sinkModel', 'crypto.model.yml:4'), self.store)
        _, rejected = module.resolve(self.store)
        self.assertEqual('not-taint-flow', rejected[-1]['reason'])

    def test_trait_aliases_and_overrides(self):
        module.read_psalm(DATA / 'hierarchy.phpstub', 'fixture', self.store)
        module.expand_trait_members(self.store)
        facts, rejected = module.resolve(self.store)
        self.assertFalse(rejected)
        self.assertEqual({'vendor\\override::aliasinput', 'vendor\\override::namedinput'},
                         {fact.subject for fact in facts if fact.section == 'sources' and fact.subject.startswith('vendor\\override::')})
        self.assertTrue(any(fact.subject == 'vendor\\override::query' and fact.kind == 'sqli' for fact in facts))

    def test_missing_hierarchy(self):
        module.read_psalm(DATA / 'hierarchy.phpstub', 'fixture', self.store)
        for owner in ('vendor\\missing', 'vendor\\cyclea'):
            self.store.candidates.append(module.Candidate(owner + '::absent', 'sources', 'user-input', '', 'fixture', 'hierarchy.phpstub'))
        _, rejected = module.resolve(self.store)
        self.assertEqual(['no-signature', 'no-signature'], [row['reason'] for row in rejected])
        fact = module.ResolvedFact('vendor\\missing', 'sources', 'user-input', None)
        self.assertEqual(['UnknownParent'], module.unrecorded_parents([fact], self.store))


if __name__ == '__main__':
    unittest.main()
