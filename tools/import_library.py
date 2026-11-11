#!/usr/bin/env python3
"""Import signed library endpoints from the supplied, inert upstream checkouts.

Run with Python -I. Readers accept PHP declarations, the NEON taint subset,
and CodeQL MaD row arrays; no upstream module or script is imported.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path

SCRIPT = 'tools/import_library.py'
UPSTREAMS = {
    'psalm-plugin-laravel': ('psalm/psalm-plugin-laravel', 'v4.19.1', 'bfeefed6ea930f448cb0c2b5bc57e8948ee78531'),
    'psalm-plugin-doctrine': ('psalm/psalm-plugin-doctrine', 'v2.11.1', '2a6bffef421f9a5959204b28179ce9ab4376ae0d'),
    'phpstan-security': ('nth-root/phpstan-security', 'v0.3.0', '6d4a940bf01fc48afe161a5d9e0a2bffeb12ec46'),
    'psalm': ('vimeo/psalm', '7.2.1', '127f608db981d5e1d023603514f7bbfcaae8f570'),
    'codeql-php': ('Vozec/codeql-php', 'untagged', '448ec77f9d5286d38c20ecc5fa79bd58a4128432'),
    'framework': ('laravel/framework', 'v13.40.0', '1449bf241017087fbd38c118ecaabef3f6797fdc'),
    'dbal': ('doctrine/dbal', '4.5.1', 'b2815456989aa41964ee66d7ab47b7885264acf3'),
    'browsershot': ('spatie/browsershot', '5.5.0', 'eba71ab7f4aba23d9321d653ccd19d4e94432516'),
    'filesystem': ('symfony/filesystem', 'v7.4.23', '53d609da66578dad5a39fe290e8f924ec8f05e93'),
    'http-foundation': ('symfony/http-foundation', 'v7.4.23', '7fb73cffa06e2bcc2cb523fcccb1e8174106b206'),
    'framework-bundle': ('symfony/framework-bundle', 'v7.4.23', '6a749f2c37cb9def53793633ec72958aaad4b359'),
    'dom-crawler': ('symfony/dom-crawler', 'v7.4.22', 'cc5c3d6275873fd463c2a772251d65379015682f'),
    'ldap': ('symfony/ldap', 'v7.4.10', 'bba9e535d29c15bd6842bf85bc341debfbb4bcb3'),
    'process': ('symfony/process', 'v7.4.22', 'a5a6912edbbfc4c98cd080bc4bbe37c8e7eeb20a'),
}
# Origins that are library releases: their own PHP sources declare the package's classes.
LIBRARY_RELEASES = ('framework', 'dbal', 'browsershot', 'filesystem', 'http-foundation',
                    'framework-bundle', 'dom-crawler', 'ldap', 'process')
PSALM_PACKAGES = {
    'amphp/amp': ('amphp/amp', '3'),
    'amphp/byte-stream': ('amphp/byte-stream', '2'),
    'amphp/file': ('amphp/file', '3'),
    'amphp/http-client': ('amphp/http-client', '5'),
    'amphp/process': ('amphp/process', '2'),
    'guzzlehttp/guzzle': ('guzzlehttp/guzzle', '7'),
    'guzzlehttp/psr7': ('guzzlehttp/psr7', '2'),
    'guzzlehttp/promises': ('guzzlehttp/promises', 'unknown'),
    'psr/http-client': ('psr/http-client', 'unknown'),
    'psr/http-message': ('psr/http-message', '1 and 2'),
    'psr/log': ('psr/log', 'unknown'),
    'mongodb/mongodb': ('mongodb/mongodb', '2.4'),
    'monolog/monolog': ('monolog/monolog', '3.12.1'),
    'webmozart/assert': ('webmozart/assert', '2.4'),
    'webklex/php-imap': ('webklex/php-imap', 'unknown'),
    'jcupitt/vips': ('jcupitt/vips', 'unknown'),
    'phpoffice/phpspreadsheet': ('phpoffice/phpspreadsheet', '5'),
    'pear/archive_tar': ('pear/archive_tar', 'unknown'),
    'smi2/phpclickhouse': ('smi2/phpclickhouse', 'unknown'),
}
CODEQL_KINDS = {
    'sql-injection': 'sqli', 'SQL injection': 'sqli',
    'command-injection': 'cmdi', 'command injection': 'cmdi',
    'code-injection': 'codei', 'code injection': 'codei',
    'xss': 'xss', 'cross-site scripting': 'xss', 'reflected XSS': 'xss',
    'path-injection': 'pathtrav', 'path traversal': 'pathtrav', 'file read': 'pathtrav',
    'ldap-injection': 'ldapi', 'LDAP injection': 'ldapi', 'ldap injection': 'ldapi',
    'url-redirect': 'openredirect', 'open redirect': 'openredirect',
    'server-side request forgery': 'ssrf', 'ssrf': 'ssrf',
    'unsafe deserialization': 'deser', 'insecure deserialization': 'deser',
    'file inclusion': 'fileinc', 'XPath injection': 'xpathi', 'xpath injection': 'xpathi',
    'template injection': 'templatei',
    'NoSQL injection': 'nosqli', 'nosql-injection': 'nosqli',
}
NEON_KINDS = {
    'sql': ('sqli',), 'html': ('xss',), 'shell': ('cmdi',),
    'path': ('pathtrav', 'ssrf'), 'include': ('fileinc',),
    'redirect': ('openredirect',), 'unserialize': ('deser',),
    'callable': ('callablei',), 'eval': ('codei',),
    'xpath': ('xpathi',), 'ldap': ('ldapi',),
}
CODEQL_SOURCES = {
    **dict.fromkeys(('cacti-request codeigniter-request drupal-request joomla-request librenms-request '
                     'magento-request magento-request-body magento-request-cookie moodle-request october-request '
                     'phpbb-request prestashop-input spip-request symfony-request symfony-request-body txp-request '
                     'typo3-request wordpress-query-var wordpress-request yii-request contao-input e107-request '
                     'magento-request-file magento-request-header magento-request-server mediawiki-request '
                     'modx-processor-request processwire-request silverstripe-request xoops-request').split(), 'user-input'),
    'remote': 'user-input', 'laravel-request': 'user-input',
    'database': 'external-input', 'file': 'external-input',
    'stored': 'external-input', 'environment': 'external-input',
}
BUILTIN_TYPES = set('mixed void never null bool true false int float string array object callable iterable self static parent resource'.split())
TOKEN = re.compile(r'/\*.*?\*/|//[^\n]*|\#\[|<<<[ \t]*([\'"]?)(\w+)\1\r?\n.*?\r?\n[ \t]*\2\b|\#[^\n]*|\s+|<\?php|\?>|\'(?:\\.|[^\'\\])*\'|"(?:\\.|[^"\\])*"|\$\w+|\\?[A-Za-z_\x80-\uffff][\w\\\x80-\uffff]*|\.\.\.|::|=>|.', re.S)
MODIFIERS = {'public', 'protected', 'private', 'static', 'abstract', 'final', 'readonly'}


@dataclass
class Declaration:
    subject: str
    kind: str
    signature: dict
    origin: str
    location: str
    package: str = ''


@dataclass(frozen=True)
class Candidate:
    subject: str
    section: str
    kind: str
    parameter: str
    origin: str
    location: str
    reason: str = ''


@dataclass
class ImportData:
    signatures: dict[str, Declaration] = field(default_factory=dict)
    candidates: list[Candidate] = field(default_factory=list)
    traits: dict[str, list[str]] = field(default_factory=dict)
    trait_aliases: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    psalm_kinds: dict[str, str] = field(default_factory=lambda: {'sql': 'sqli', 'shell': 'cmdi', 'input': 'user-input'})


@dataclass
class ResolvedFact:
    subject: str
    section: str
    kind: str
    position: int | None
    origins: set[str] = field(default_factory=set)


@dataclass
class Scope:
    namespace: str = ''
    aliases: dict[str, str] = field(default_factory=dict)
    owner: str = ''


def qualify(name: str, scope: Scope) -> str:
    if name.startswith('\\'):
        return name[1:]
    if name.lower() in BUILTIN_TYPES:
        return name
    head, *tail = name.split('\\')
    if head.lower() in scope.aliases:
        return '\\'.join([scope.aliases[head.lower()], *tail])
    return '\\'.join(filter(None, [scope.namespace, name]))


def php_type(tokens: list[str], scope: Scope) -> str:
    return ''.join(qualify(token, scope) if re.fullmatch(r'\\?[A-Za-z_][\w\\]*', token) else token
                   for token in tokens) or 'mixed'


def end_of(tokens: list[str], start: int) -> int:
    close = {'(': ')', '[': ']', '{': '}'}[tokens[start]]
    index = start + 1
    while index < len(tokens):
        if tokens[index] == close:
            return index
        index = end_of(tokens, index) + 1 if tokens[index] in ('(', '[', '{') else index + 1
    raise ValueError(f'unclosed {tokens[start]} at token {start}')


def split_tokens(tokens: list[str]) -> list[list[str]]:
    result, start, index = [], 0, 0
    while index < len(tokens):
        if tokens[index] == ',':
            result.append(tokens[start:index])
            start = index + 1
        index = end_of(tokens, index) + 1 if tokens[index] in ('(', '[', '{') else index + 1
    return [part for part in result + [tokens[start:]] if part]


def parameter(tokens: list[str], scope: Scope) -> dict:
    position = next(index for index, token in enumerate(tokens) if token.startswith('$'))
    prefix = [token for token in tokens[:position] if token not in MODIFIERS]
    by_ref = bool(prefix and prefix[-1] == '&' or len(prefix) > 1 and prefix[-2:] == ['&', '...'])
    if by_ref:
        prefix.pop(-1 if prefix[-1] == '&' else -2)
    prefix = [token for token in prefix if token != '...']
    value = {'name': tokens[position][1:], 'type': php_type(prefix, scope)}
    if '...' in tokens[:position]:
        value['variadic'] = True
    if by_ref:
        value['byRef'] = True
    if '=' in tokens[position + 1:]:
        value['optional'] = True
        default = ''.join(tokens[tokens.index('=') + 1:])
        if re.fullmatch(r"null|true|false|-?\d+(?:\.\d+)?|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", default):
            value['default'] = default
    return value


def annotations(doc: str, declaration: Declaration, store: ImportData) -> None:
    for tag, value in re.findall(r'^\s*(?:/\*\*|\*)?\s*@psalm-taint-(sink|source|escape)\s+([^\n]*?)(?:\*/)?$', doc, re.M):
        fields = value.strip().split()
        kind = fields[0] if fields else ''
        section = {'sink': 'sinks', 'source': 'sources', 'escape': 'sanitizers'}[tag]
        param = fields[1].lstrip('$') if tag == 'sink' and len(fields) == 2 else ''
        mapped = store.psalm_kinds.get(kind)
        reason = '' if mapped and mapped != 'ignore' else 'no-cwe-kind'
        if value.strip().startswith('('):
            reason = 'unsupported-condition'
        if tag == 'sink' and not param:
            reason = 'unsupported-annotation'
        store.candidates.append(Candidate(declaration.subject, section, mapped or kind, param,
                                          declaration.origin, declaration.location, reason))


def read_callable(tokens: list[str], scope: Scope, context: tuple) -> int:
    index, doc, origin, location, store = context
    name_index = index + 2 if tokens[index + 1] == '&' else index + 1
    if tokens[name_index + 1] != '(':
        raise ValueError(f'{location}: unsupported callable declaration')
    last = end_of(tokens, name_index + 1)
    tail = last + 1
    while tokens[tail] not in ('{', ';'):
        tail += 1
    params = [parameter(part, scope) for part in split_tokens(tokens[name_index + 2:last])]
    result_type = tokens[last + 2:tail] if tokens[last + 1] == ':' else []
    signature = {'params': params, 'returnType': php_type(result_type, scope)}
    subject = f'{scope.owner}::{tokens[name_index]}' if scope.owner else qualify(tokens[name_index], scope)
    declaration = Declaration(subject.lower(), 'method' if scope.owner else 'function', signature, origin, location)
    store.signatures[declaration.subject] = declaration
    annotations(doc, declaration, store)
    return end_of(tokens, tail) + 1 if tokens[tail] == '{' else tail + 1


def read_class(tokens: list[str], scope: Scope, context: tuple) -> int:
    index, origin, location, store = context
    name = qualify(tokens[index + 1], scope)
    start = tokens.index('{', index + 2)
    signature = {'classifier': tokens[index], 'name': name}
    class_edges(tokens[index + 2:start], scope, signature)
    declaration = Declaration(name.lower(), 'class', signature, origin, location)
    store.signatures[declaration.subject] = declaration
    end = end_of(tokens, start)
    store.traits.setdefault(declaration.subject, [])
    store.trait_aliases.setdefault(declaration.subject, [])
    scan_php(tokens[start + 1:end], Scope(scope.namespace, dict(scope.aliases), name), (origin, location, store))
    return end + 1


def class_edges(tokens: list[str], scope: Scope, signature: dict) -> None:
    relation = ''
    for token in tokens:
        if token in ('extends', 'implements'):
            relation = token
        elif token != ',' and relation:
            name = qualify(token, scope)
            if relation == 'extends' and signature['classifier'] == 'class':
                signature['parent'] = name
            else:
                signature.setdefault('interfaces', []).append(name)


def read_traits(tokens: list[str], index: int, context: tuple) -> int:
    scope, store = context
    end = index + 1
    while tokens[end] not in (';', '{'):
        end += 1
    store.traits[scope.owner.lower()].extend(qualify(part[0], scope) for part in split_tokens(tokens[index + 1:end]))
    if tokens[end] == '{':
        last = end_of(tokens, end)
        read_trait_aliases(tokens[end + 1:last], scope, store)
        return last + 1
    return end + 1


def read_trait_aliases(tokens: list[str], scope: Scope, store: ImportData) -> None:
    for clause in ' '.join(tokens).split(';'):
        parts = clause.split()
        if not parts:
            continue
        if 'as' not in parts:
            raise ValueError(f'unsupported trait adaptation: {clause}')
        source = qualify(parts[0], scope).lower() + '::' + parts[2].lower() if '::' in parts else parts[0].lower()
        alias = parts[-1]
        if alias not in MODIFIERS:
            store.trait_aliases[scope.owner.lower()].append((source, alias.lower()))


def read_use(tokens: list[str], index: int, scope: Scope) -> int:
    end = tokens.index(';', index)
    if tokens[index + 1] in ('function', 'const'):
        return end + 1
    for part in split_tokens(tokens[index + 1:end]):
        if '{' in part:
            prefix = part[0]
            for item in split_tokens(part[2:-1]):
                full = prefix + item[0]
                scope.aliases[(item[-1] if 'as' in item else item[0].split('\\')[-1]).lower()] = full.lstrip('\\')
            continue
        full = part[0].lstrip('\\')
        scope.aliases[(part[-1] if 'as' in part else full.split('\\')[-1]).lower()] = full
    return end + 1


def scan_php(tokens: list[str], scope: Scope, context: tuple) -> None:
    index, doc = 0, ''
    origin, location, store = context
    while index < len(tokens):
        token = tokens[index]
        if token.startswith('/**'):
            doc, index = token, index + 1
        elif token == 'namespace':
            index = read_namespace(tokens, index, context)
        elif token == 'use':
            index = read_traits(tokens, index, (scope, store)) if scope.owner else read_use(tokens, index, scope)
        elif token in ('class', 'interface', 'trait', 'enum') and tokens[index - 1] != '::':
            index, doc = read_class(tokens, scope, (index, origin, location, store)), ''
        elif token == 'function':
            index, doc = read_callable(tokens, scope, (index, doc, origin, location, store)), ''
        elif token == '{':
            index = end_of(tokens, index) + 1
        else:
            index += 1
            if token not in MODIFIERS:
                doc = ''


def read_namespace(tokens: list[str], index: int, context: tuple) -> int:
    start = index + 1
    while tokens[start] not in ('{', ';'):
        start += 1
    namespace = ''.join(tokens[index + 1:start])
    if tokens[start] == '{':
        end = end_of(tokens, start)
        scan_php(tokens[start + 1:end], Scope(namespace), context)
        return end + 1
    end = next((pos for pos in range(start + 1, len(tokens)) if tokens[pos] == 'namespace' and tokens[pos - 1] not in ('>', '::')),
               len(tokens))
    scan_php(tokens[start + 1:end], Scope(namespace), context)
    return end


def without_attributes(tokens: list[str]) -> list[str]:
    """Drop PHP attribute groups, which may sit inside a parameter list."""
    result, index = [], 0
    while index < len(tokens):
        if tokens[index] == '#[':
            depth = 1
            index += 1
            while depth:
                depth += (tokens[index] == '[') - (tokens[index] == ']')
                index += 1
        else:
            result.append(tokens[index])
            index += 1
    return result


def read_psalm(path: Path, origin: str, store: ImportData) -> None:
    """Read declarations and exact endpoint tags from PHP stub text without execution."""
    text = path.read_text(encoding='utf-8')
    tokens = without_attributes([token for token in (match[0] for match in TOKEN.finditer(text))
                                 if not token.isspace() and not token.startswith(('//', '<?', '?>'))
                                 and (token == '#[' or not token.startswith('#'))
                                 and (not token.startswith('/*') or token.startswith('/**'))])
    location = '/'.join(path.parts[path.parts.index('stubs') + 1:]) if 'stubs' in path.parts else path.name
    scan_php(tokens, Scope(), (origin, location, store))


def read_neon(path: Path, store: ImportData) -> None:
    """Read the indentation and inline endpoint records of the supplied NEON taint lists."""
    section, owner, category = '', '', ''
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        text = line.split('#', 1)[0].strip()
        if text in ('sources:', 'sinks:', 'flows:'):
            section, owner = text[:-1], ''
        elif text in ('methods:', 'functions:', 'variables:'):
            category, owner = text[:-1], ''
        elif section == 'sources' and category == 'methods' and ': [' in text:
            name, values = text.split(': [', 1)
            for method in values.rstrip(']').split(','):
                store.candidates.append(Candidate(f'{name}::{method.strip()}'.lower(), section, 'user-input', '', 'phpstan-security', f'{path.name}:{number}'))
        elif text.endswith(':') and '\\' in text:
            owner = text[:-1]
        elif section == 'sinks' and '{type:' in text:
            neon_sink(text, (owner if category == 'methods' else '', f'{path.name}:{number}'), store)


def neon_sink(text: str, context: tuple[str, str], store: ImportData) -> None:
    owner, location = context
    match = re.fullmatch(r'(\w+):\s*\{type:\s*(\w+),\s*parameters:\s*\[([^]]*)]\}', text)
    if not match:
        raise ValueError(f'{location}: unsupported NEON sink: {text}')
    name, kind, parameters = match.groups()
    subject = f'{owner}::{name}' if owner else name
    for parameter_name in parameters.split(','):
        for mapped in NEON_KINDS.get(kind, (kind,)):
            reason = '' if kind in NEON_KINDS else 'no-cwe-kind'
            store.candidates.append(Candidate(subject.lower(), 'sinks', mapped, parameter_name.strip(),
                                              'phpstan-security', location, reason))


def read_codeql(path: Path, store: ImportData) -> None:
    """Read inline MaD arrays; model family fixes each row's column meanings."""
    family = ''
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        match = re.search(r'extensible:\s*(\w+)', line)
        if match:
            family = match[1]
        if not re.match(r'\s*-\s*\[', line):
            continue
        row_text = line[line.index('['):]
        row, _ = json.JSONDecoder().raw_decode(row_text)
        codeql_row(row, (family, f'{path.name}:{number}'), store)


def codeql_row(row: list, context: tuple[str, str], store: ImportData) -> None:
    family, location = context
    if family not in ('sinkModel', 'typedSinkModel', 'sourceModel', 'typedSourceModel', 'sanitizerModel', 'typedSanitizerModel'):
        return
    typed = family.startswith('typed')
    subject = f'{row[0]}::{row[1]}' if typed else str(row[1])
    reason = '' if typed or '::' in subject else 'no-class'
    section = 'sinks' if 'Sink' in family or family == 'sinkModel' else 'sources'
    section = 'sanitizers' if 'anitizer' in family else section
    parameter_name = str(row[2]) if section == 'sinks' else ''
    raw_kind = str(row[-1]) if section != 'sanitizers' else ''
    mapping = CODEQL_KINDS if section != 'sources' else CODEQL_SOURCES
    kind = mapping.get(raw_kind, raw_kind)
    reason = reason or ('' if raw_kind in mapping else 'no-cwe-kind')
    if raw_kind == 'hardcoded-crypto-key':
        reason = 'not-taint-flow'
    store.candidates.append(Candidate(subject.lower().lstrip('\\'), section, kind, parameter_name,
                                      'codeql-php', location, reason))


def candidate_positions(candidate: Candidate, signature: dict) -> list[int | None]:
    if candidate.section != 'sinks':
        return [None]
    params = signature.get('params', [])
    if candidate.parameter == '-1':
        return list(range(len(params)))
    if candidate.parameter.isdecimal():
        position = int(candidate.parameter)
        return [position] if position < len(params) else []
    return [index for index, param in enumerate(params) if param['name'] == candidate.parameter]


def rejection(candidate: Candidate, reason: str) -> dict:
    return {'subject': candidate.subject, 'section': candidate.section, 'kind': candidate.kind,
            'parameter': candidate.parameter, 'upstream': candidate.origin,
            'location': candidate.location, 'reason': reason}


def inherited_declaration(subject: str, store: ImportData, visited: set[str]) -> Declaration | None:
    if subject in store.signatures:
        return store.signatures[subject]
    if '::' not in subject or subject in visited:
        return None
    visited.add(subject)
    owner, member = subject.split('::')
    declaration = store.signatures.get(owner)
    if declaration is None:
        return None
    signature = declaration.signature
    supers = store.traits.get(owner, []) + ([signature['parent']] if 'parent' in signature else []) + signature.get('interfaces', [])
    for parent in supers:
        found = inherited_declaration(f'{parent.lower()}::{member}', store, visited)
        if found:
            return found
    return None


def trait_owners(owner: str, store: ImportData, visited: set[str]) -> set[str]:
    if owner in visited:
        return set()
    visited.add(owner)
    owners = set()
    for trait in store.traits.get(owner, []):
        owners.add(trait.lower())
        owners.update(trait_owners(trait.lower(), store, visited))
    return owners


def expand_trait_members(store: ImportData) -> None:
    """Materialize trait methods because ClassSignature has no trait-use field."""
    declarations = list(store.signatures.values())
    candidates = list(store.candidates)
    additions = {}
    for owner in store.traits:
        traits = trait_owners(owner, store, set())
        members = [item for item in declarations if item.kind == 'method' and item.subject.split('::')[0] in traits]
        for member in members:
            subject = owner + '::' + member.subject.split('::')[1]
            resolved = inherited_declaration(subject, store, set())
            if subject in store.signatures or resolved is not member:
                continue
            add_trait_member((subject, member, candidates), additions, store)
        for source, alias in store.trait_aliases.get(owner, []):
            member = trait_alias_declaration(owner, source, store)
            if member is None:
                continue
            add_trait_member((owner + '::' + alias, member, candidates), additions, store)
    store.signatures.update(additions)


def add_trait_member(context: tuple, additions: dict[str, Declaration], store: ImportData) -> None:
    subject, member, candidates = context
    owner = subject.split('::')[0]
    additions[subject] = replace(member, subject=subject, package=store.signatures[owner].package)
    store.candidates.extend(replace(item, subject=subject) for item in candidates if item.subject == member.subject)


def trait_alias_declaration(owner: str, source: str, store: ImportData) -> Declaration | None:
    if '::' in source:
        return inherited_declaration(source, store, set())
    for trait in store.traits.get(owner, []):
        declaration = inherited_declaration(trait.lower() + '::' + source, store, set())
        if declaration:
            return declaration
    return None


def resolve(store: ImportData) -> tuple[list[ResolvedFact], list[dict]]:
    """Union canonical facts; keep every discarded input with a specific reason."""
    facts, rejected = {}, []
    for candidate in store.candidates:
        declaration = inherited_declaration(candidate.subject, store, set())
        reason = candidate.reason if candidate.reason in ('no-class', 'not-taint-flow') else ('no-signature' if declaration is None else candidate.reason)
        positions = [] if reason else candidate_positions(candidate, declaration.signature)
        reason = reason or ('' if positions else 'unresolved-parameter')
        if reason:
            rejected.append(rejection(candidate, reason))
            continue
        if candidate.subject not in store.signatures:
            owner = store.signatures[candidate.subject.split('::')[0]]
            store.signatures[candidate.subject] = replace(declaration, subject=candidate.subject, package=owner.package)
        for position in positions:
            key = (candidate.subject, candidate.section, candidate.kind, position)
            fact = facts.setdefault(key, ResolvedFact(*key))
            fact.origins.add(candidate.origin)
    return list(facts.values()), rejected


def yaml_scalar(value: str | int | bool | None) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_lines(value: dict | list | str | int | bool | None, indent: int = 0) -> list[str]:
    prefix = ' ' * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines += [f'{prefix}{key}:'] + yaml_lines(item, indent + 2)
            else:
                lines.append(f'{prefix}{key}: {yaml_scalar(item)}')
        return lines
    if isinstance(value, list):
        return [line for item in value for line in ([prefix + '-'] + yaml_lines(item, indent + 2))]
    return [prefix + yaml_scalar(value)]


def yaml_text(value: dict | list) -> str:
    return '\n'.join(yaml_lines(value)) + '\n'


def psalm_mapping(path: Path) -> dict[str, str]:
    return dict(re.findall(r'^  ([\w-]+): ([\w-]+)$', path.read_text(encoding='utf-8'), re.M))


def files_under(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob('*') if path.suffix in ('.phpstub', '.stubphp', '.php'))


def doctrine_package(subject: str) -> str:
    if subject.startswith('doctrine\\dbal\\'):
        return 'doctrine/dbal'
    if subject.startswith('doctrine\\common\\collections\\'):
        return 'doctrine/collections'
    if subject.startswith('doctrine\\persistence\\'):
        return 'doctrine/persistence'
    return 'doctrine/orm'


def read_stub_files(paths: list[Path], context: tuple, store: ImportData) -> None:
    origin, package = context
    for path in paths:
        before = set(store.signatures)
        read_psalm(path, origin, store)
        for declaration in store.signatures.values():
            if declaration.package and declaration.subject in before:
                continue
            declaration.package = doctrine_package(declaration.subject) if package == 'doctrine' else package


def release_sources(root: Path) -> list[Path]:
    """List the release's class files: PSR-4 files named for a class, outside the classmap exclusions."""
    autoload = json.loads((root / 'composer.json').read_text(encoding='utf-8'))['autoload']
    directories = [root / target for targets in autoload['psr-4'].values()
                   for target in ([targets] if isinstance(targets, str) else targets)]
    excluded = [root / part.strip('/') for part in autoload.get('exclude-from-classmap', [])]
    return sorted({path for directory in directories for path in files_under(directory)
                   if path.name[0].isupper() and not any(path.is_relative_to(part) for part in excluded)})


def load_releases(upstream: Path, store: ImportData) -> dict[str, str]:
    """Read the pinned library releases; the plugin stubs read afterwards replace a class both declare."""
    for origin in LIBRARY_RELEASES:
        name = UPSTREAMS[origin][0]
        read_stub_files(release_sources(upstream / origin), (origin, name), store)
    return {UPSTREAMS[origin][0]: UPSTREAMS[origin][1].removeprefix('v') for origin in LIBRARY_RELEASES}


def load_stubs(upstream: Path, store: ImportData) -> dict[str, str]:
    laravel = upstream / 'psalm-plugin-laravel' / 'stubs'
    versions = sorted((path for path in laravel.iterdir() if re.fullmatch(r'\d+(?:\.\d+)*', path.name)),
                      key=lambda path: tuple(int(part) for part in path.name.split('.')))
    read_stub_files(files_under(laravel / 'common'), ('psalm-plugin-laravel', 'laravel/framework'), store)
    for version in versions:
        read_stub_files(files_under(version), ('psalm-plugin-laravel', 'laravel/framework'), store)
    read_stub_files(files_under(upstream / 'psalm-plugin-doctrine' / 'stubs'), ('psalm-plugin-doctrine', 'doctrine'), store)
    library_root = upstream / 'psalm' / 'stubs' / 'libraries'
    for path in files_under(library_root):
        package, _ = PSALM_PACKAGES[path.relative_to(library_root).with_suffix('').as_posix()]
        read_stub_files([path], ('psalm', package), store)
    return {'laravel/framework': versions[-1].name, 'doctrine/dbal': 'unknown', 'doctrine/orm': '^2.6',
            'doctrine/collections': '^1.8 || ^2.0', 'doctrine/persistence': '^2.0',
            **{package: version for package, version in PSALM_PACKAGES.values()}}


def package_for(candidate: Candidate, store: ImportData) -> str:
    declaration = store.signatures.get(candidate.subject)
    if declaration:
        return declaration.package
    if candidate.subject.startswith('browsershot::'):
        return 'spatie/browsershot'
    if candidate.subject.startswith('illuminate\\') or candidate.location.startswith('laravel.'):
        return 'laravel/framework'
    if candidate.subject.startswith('doctrine\\') or candidate.location.startswith('doctrine.'):
        return doctrine_package(candidate.subject)
    if candidate.subject.startswith('symfony\\'):
        parts = candidate.subject.split('\\')
        component = {'httpfoundation': 'http-foundation', 'domcrawler': 'dom-crawler',
                     'frameworkbundle': 'framework-bundle'}.get(parts[2], parts[2])
        return 'symfony/' + component
    file_name = candidate.location.split('.', 1)[0]
    return f'unassigned/{file_name}'


def qualify_candidates(store: ImportData) -> None:
    declarations = list(store.signatures.values())
    rule_declarations = [item for item in declarations if item.origin not in LIBRARY_RELEASES]
    for index, candidate in enumerate(store.candidates):
        if candidate.origin != 'codeql-php' or candidate.reason == 'no-class' or '\\' in candidate.subject:
            continue
        package = package_for(candidate, store)
        owner, separator, member = candidate.subject.partition('::')
        matches = next((found for found in (
            [item.subject + separator + member for item in pool if item.package == package
             and item.kind == 'class' and item.subject.rsplit('\\', 1)[-1] == owner]
            for pool in (rule_declarations, declarations)) if found), [])
        if len(matches) == 1:
            store.candidates[index] = Candidate(matches[0], candidate.section, candidate.kind, candidate.parameter,
                                                 candidate.origin, candidate.location, candidate.reason)


def normalize_sources(store: ImportData) -> None:
    for index, candidate in enumerate(store.candidates):
        if candidate.section != 'sources' or candidate.kind != 'user-input':
            continue
        subject = candidate.subject
        external = candidate.origin == 'psalm' or subject.startswith((
            'illuminate\\http\\client\\response::', 'illuminate\\session\\store::')) or subject == 'session'
        if external:
            store.candidates[index] = Candidate(subject, candidate.section, 'external-input', candidate.parameter,
                                                 candidate.origin, candidate.location, candidate.reason)


def endpoint_entry(declaration: Declaration, facts: list[ResolvedFact]) -> dict:
    entry = {'subject': {declaration.kind: declaration.subject}, 'signature': declaration.signature}
    for fact in sorted(facts, key=lambda item: (item.section, item.position or 0, item.kind)):
        if fact.section == 'sinks':
            value = {'port': f'argument({fact.position})', 'vulnType': fact.kind}
        elif fact.section == 'sources':
            value = {'sourceKinds': [fact.kind]}
        else:
            value = {'vulnTypes': [fact.kind]}
        entry.setdefault(fact.section, []).append(value)
    return entry


def upstream_label(origin: str) -> str:
    name, release, commit = UPSTREAMS[origin]
    return f'{name} {release} ({commit})'


def mit_doctrine(upstream: Path) -> str:
    composer = json.loads((upstream / 'psalm-plugin-doctrine' / 'composer.json').read_text(encoding='utf-8'))
    if composer['license'] != 'MIT':
        raise ValueError('Doctrine plugin license is not MIT')
    holder = ', '.join(author['name'] for author in composer['authors'])
    laravel_notice = (upstream / 'psalm-plugin-laravel' / 'LICENSE').read_text(encoding='utf-8')
    permission = laravel_notice[laravel_notice.index('Permission is hereby granted'):]
    return f'MIT License\n\nCopyright (c) {holder}\n\n{permission}'


def license_text(origin: str, upstream: Path) -> str:
    if origin == 'psalm-plugin-doctrine':
        return mit_doctrine(upstream)
    notice = next(path for path in (upstream / origin / 'LICENSE', upstream / origin / 'LICENSE.md') if path.is_file())
    return notice.read_text(encoding='utf-8')


def notices(origins: set[str], upstream: Path) -> dict[str, str]:
    return {f'LICENSE-{origin}.txt': license_text(origin, upstream) for origin in sorted(origins)}


def hierarchy_subjects(subjects: set[str], store: ImportData) -> set[str]:
    result, pending = set(subjects), list(subjects)
    while pending:
        subject = pending.pop()
        declaration = store.signatures[subject]
        if declaration.kind != 'class':
            continue
        signature = declaration.signature
        names = store.traits.get(subject, []) + signature.get('interfaces', [])
        names += [signature['parent']] if 'parent' in signature else []
        for name in names:
            key = name.lower()
            if key in store.signatures and key not in result:
                result.add(key)
                pending.append(key)
    return result


def package_subjects(facts: list[ResolvedFact], store: ImportData) -> set[str]:
    subjects = {fact.subject for fact in facts}
    subjects.update(fact.subject.split('::')[0] for fact in facts if '::' in fact.subject)
    return hierarchy_subjects(subjects, store)


def unrecorded_parents(facts: list[ResolvedFact], store: ImportData) -> list[str]:
    signatures = [store.signatures[subject].signature for subject in package_subjects(facts, store)]
    return sorted({signature['parent'] for signature in signatures
                   if 'parent' in signature and signature['parent'].lower() not in store.signatures})


def package_output(package: str, context: tuple, store: ImportData) -> tuple[dict[str, str], dict]:
    facts, rejections, upstream, version = context
    by_subject = defaultdict(list)
    for fact in facts:
        by_subject[fact.subject].append(fact)
    subjects = package_subjects(facts, store)
    declarations = [store.signatures[subject] for subject in sorted(subjects)]
    origins = {origin for fact in facts for origin in fact.origins} | {item.origin for item in declarations}
    origins |= {item['upstream'] for item in rejections}
    header = '# Generated by tools/import_library.py from ' + ', '.join(upstream_label(origin) for origin in sorted(origins)) + '.\n'
    document = header
    for declaration in declarations:
        entry_origins = {declaration.origin} | {origin for fact in by_subject[declaration.subject] for origin in fact.origins}
        document += '# from: ' + ', '.join(sorted(entry_origins)) + '\n'
        document += yaml_text([endpoint_entry(declaration, by_subject[declaration.subject])])
    filename = package.replace('/', '-') + '.yaml'
    if not declarations:
        return {'rejections.json': json.dumps(rejections, indent=2) + '\n', **notices(origins, upstream)}, {}
    output = {filename: document,
              'provenance.yaml': header + yaml_text({'producer': SCRIPT + ' over ' + ', '.join(upstream_label(origin) for origin in sorted(origins)), 'verification': 'generated'}),
              'rejections.json': json.dumps(sorted(rejections, key=lambda row: json.dumps(row, sort_keys=True)), indent=2, ensure_ascii=False) + '\n',
              **notices(origins, upstream)}
    catalog = {'package': package, 'version': version, 'upstreams': [upstream_label(origin) for origin in sorted(origins)],
               'root': '/taint-libraries/' + package.replace('/', '-') + '/'}
    return output, catalog


def generate(upstream: Path, resources: Path) -> dict[str, str]:
    store = ImportData(psalm_kinds=psalm_mapping(resources / 'vocabulary' / 'psalm-mapping.yaml'))
    releases = load_releases(upstream, store)
    versions = {**load_stubs(upstream, store), **releases}
    for path in sorted((upstream / 'phpstan-security' / 'config' / 'taint').glob('*.neon')):
        if path.name != 'php.neon':
            read_neon(path, store)
    for path in sorted((upstream / 'codeql-php' / 'php' / 'ql' / 'lib' / 'ext').glob('*.model.yml')):
        if path.name != 'php-builtins.model.yml':
            read_codeql(path, store)
    expand_trait_members(store)
    qualify_candidates(store)
    normalize_sources(store)
    facts, rejected = resolve(store)
    return generated_packages((facts, rejected, upstream, versions), store)


def generated_packages(context: tuple, store: ImportData) -> dict[str, str]:
    facts, rejected, upstream, versions = context
    grouped, rejected_by = defaultdict(list), defaultdict(list)
    for fact in facts:
        grouped[store.signatures[fact.subject].package].append(fact)
    for row in rejected:
        candidate = Candidate(row['subject'], row['section'], row['kind'], row['parameter'], row['upstream'], row['location'])
        rejected_by[package_for(candidate, store)].append(row)
    output, catalog, summary = {}, [], {}
    for package in sorted(set(grouped) | set(rejected_by)):
        files, item = package_output(package, (grouped[package], rejected_by[package], upstream, versions.get(package, 'unknown')), store)
        output.update({package.replace('/', '-') + '/' + name: text for name, text in files.items()})
        if grouped[package]:
            catalog.append(item)
        summary[package] = {'entries': sum(text.startswith('  subject:') for text in files.get(package.replace('/', '-') + '.yaml', '').splitlines()),
                            'facts': dict(sorted(Counter(f'{fact.section}:{fact.kind}' for fact in grouped[package]).items())),
                            'rejections': dict(sorted(Counter(row['reason'] for row in rejected_by[package]).items())),
                            'unrecordedParents': unrecorded_parents(grouped[package], store)}
    header = '# Generated by tools/import_library.py from ' + ', '.join(upstream_label(origin) for origin in UPSTREAMS) + '.\n'
    output['catalog.yaml'] = header + '# Versions describe the upstream stubs or the pinned library release.\n' + yaml_text(catalog)
    output['summary.json'] = json.dumps(summary, indent=2, sort_keys=True) + '\n'
    return output


def write_output(output: dict[str, str], root: Path, check: bool) -> bool:
    existing = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
    changed = []
    for name in sorted(existing | output.keys()):
        path = root / name
        old = path.read_text(encoding='utf-8') if path.is_file() else ''
        new = output.get(name, '')
        if old == new:
            continue
        changed.append(name)
        if check:
            print(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=name, tofile='regenerated/' + name)), end='')
        elif name in output:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new, encoding='utf-8')
        else:
            path.unlink()
    print(json.dumps({'operation': 'import_library', 'outcome': 'different' if check and changed else 'ok', 'changed': len(changed), 'files': len(output)}))
    return not (check and changed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstreams', required=True, type=Path)
    parser.add_argument('--resources', type=Path, default=Path(__file__).resolve().parents[1] / 'externs-phpstubs/src/main/resources')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for origin in UPSTREAMS:
        if not (args.upstreams / origin).is_dir():
            parser.error(f'missing upstream directory: {origin}')
    output = generate(args.upstreams, args.resources)
    if not write_output(output, args.resources / 'taint-libraries', args.check):
        sys.exit(1)


if __name__ == '__main__':
    main()
