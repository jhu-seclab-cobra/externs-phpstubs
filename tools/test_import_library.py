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
- test_release_source_syntax: attributes, heredocs and property names equal to keywords leave declarations intact.
- test_release_sources: a release's class files follow its composer.json autoload roots and exclusions.
- test_release_declares_missing_signature: a release supplies the declaration that rule sources lack.
- test_short_class_name_prefers_rule_sources: a short class name resolves among rule-source classes first.
- test_redeclared_class_keeps_trait_uses: a second declaration of a class keeps the first one's trait uses.
- test_release_sources_listed_once: a file under two autoload roots is listed once.
- test_stub_replaces_release_declaration: a rule-source declaration replaces the release declaration of the same method.
- test_release_version: the version of a pinned release is its tag without the leading v.
- test_license_notice: a release notice may be LICENSE or LICENSE.md.
"""

import importlib.util
import json
import sys
import tempfile
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

    def read_text(self, text, origin='fixture', name='Sample.php'):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            path.write_text(text, encoding='utf-8')
            module.read_psalm(path, origin, self.store)

    def test_release_source_syntax(self):
        self.read_text('''<?php
namespace Demo;

#[Attribute(Attribute::TARGET_CLASS)]
class Source
{
    public string $namespace = <<<'EOT'
    } not a brace (
    EOT;

    public function run(#[\\SensitiveParameter] string $first, #[Other([1, 2])] int $second = 1): string
    {
        return $this->namespace . self::class;
    }
}

class After
{
    public function later(): void {}
}
''')
        signature = self.store.signatures['demo\\source::run'].signature
        self.assertEqual(['first', 'second'], [param['name'] for param in signature['params']])
        self.assertEqual(['string', 'int'], [param['type'] for param in signature['params']])
        self.assertIn('demo\\after::later', self.store.signatures)

    def test_release_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'composer.json').write_text(json.dumps({'autoload': {
                'psr-4': {'Demo\\': 'src', 'Demo\\Extra\\': ['more']}, 'exclude-from-classmap': ['/src/Tests/']}}))
            for name in ('src/Kept.php', 'src/Nested/Kept.php', 'more/Other.php', 'src/Tests/Skipped.php',
                         'src/helpers.php', 'src/view.blade.php', 'outside/Outside.php'):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text('<?php')
            found = [path.relative_to(root).as_posix() for path in module.release_sources(root)]
        self.assertEqual(['more/Other.php', 'src/Kept.php', 'src/Nested/Kept.php'], found)

    def test_release_sources_listed_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'composer.json').write_text(json.dumps({'autoload': {
                'psr-4': {'Demo\\': 'src', 'Demo\\Support\\': 'src/Support'}}}))
            (root / 'src' / 'Support').mkdir(parents=True)
            (root / 'src' / 'Support' / 'Shared.php').write_text('<?php')
            found = [path.relative_to(root).as_posix() for path in module.release_sources(root)]
        self.assertEqual(['src/Support/Shared.php'], found)

    def test_stub_replaces_release_declaration(self):
        self.store = module.ImportData()
        self.read_text('<?php namespace Demo; class Box { public function put(string $path) {} public function get() {} }',
                       origin='framework')
        self.read_text('<?php namespace Demo; class Box { public function put(string $file) {} }',
                       origin='psalm-plugin-laravel')
        put = self.store.signatures['demo\\box::put']
        self.assertEqual('psalm-plugin-laravel', put.origin)
        self.assertEqual(['file'], [param['name'] for param in put.signature['params']])
        self.assertEqual('framework', self.store.signatures['demo\\box::get'].origin)

    def test_release_version(self):
        with tempfile.TemporaryDirectory() as directory:
            for origin in module.LIBRARY_RELEASES:
                (Path(directory) / origin / 'src').mkdir(parents=True)
                (Path(directory) / origin / 'composer.json').write_text(
                    json.dumps({'autoload': {'psr-4': {'Demo\\': 'src'}}}))
            versions = module.load_releases(Path(directory), module.ImportData())
        self.assertEqual(module.UPSTREAMS['dbal'][1], versions['doctrine/dbal'])
        self.assertEqual(module.UPSTREAMS['process'][1].removeprefix('v'), versions['symfony/process'])
        self.assertFalse(any(version.startswith('v') for version in versions.values()))

    def test_release_declares_missing_signature(self):
        self.store = module.ImportData()
        self.store.candidates.append(module.Candidate(
            'demo\\child::inherited', 'sinks', 'sqli', 'sql', 'phpstan-security', 'demo.neon:1'))
        self.read_text('''<?php
namespace Demo;
interface Contract { public function inherited(string $sql): void; }
class Child implements Contract {}
''', origin='demo-release')
        facts, rejected = module.resolve(self.store)
        self.assertFalse(rejected)
        self.assertEqual(['demo\\child::inherited'], [fact.subject for fact in facts])
        self.assertEqual({'demo-release'}, {self.store.signatures[fact.subject].origin for fact in facts})

    def test_short_class_name_prefers_rule_sources(self):
        self.store = module.ImportData()
        self.read_text('<?php namespace Demo\\Http; class Request { public function all() {} }', origin='psalm-plugin-laravel')
        self.read_text('<?php namespace Demo\\Facades; class Request {}', origin='framework')
        self.read_text('<?php namespace Demo\\Facades; class Storage {}', origin='framework')
        self.read_text('<?php namespace Demo\\Other; class Storage {}', origin='framework')
        for declaration in self.store.signatures.values():
            declaration.package = 'laravel/framework'
        for subject in ('Request::all', 'Storage::get'):
            self.store.candidates.append(module.Candidate(
                subject.lower(), 'sources', 'user-input', '', 'codeql-php', 'laravel.model.yml:1'))
        module.qualify_candidates(self.store)
        self.assertEqual(['demo\\http\\request::all', 'storage::get'], [item.subject for item in self.store.candidates])

    def test_redeclared_class_keeps_trait_uses(self):
        self.read_text('''<?php
namespace Demo;
trait Inner { public function only() {} }
trait Outer { use Inner; }
''', origin='release')
        self.read_text('<?php namespace Demo; trait Outer { public function input() {} }', origin='stub')
        self.read_text('<?php namespace Demo; class Holder { use Outer; }', origin='stub')
        module.expand_trait_members(self.store)
        self.assertEqual(['Demo\\Inner'], self.store.traits['demo\\outer'])
        self.assertIn('demo\\holder::only', self.store.signatures)
        self.assertIn('demo\\holder::input', self.store.signatures)

    def test_license_notice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for origin, name in (('plain', 'LICENSE'), ('markdown', 'LICENSE.md')):
                (root / origin).mkdir()
                (root / origin / name).write_text(origin + ' notice')
            self.assertEqual({'LICENSE-plain.txt': 'plain notice', 'LICENSE-markdown.txt': 'markdown notice'},
                             module.notices({'plain', 'markdown'}, root))


if __name__ == '__main__':
    unittest.main()
