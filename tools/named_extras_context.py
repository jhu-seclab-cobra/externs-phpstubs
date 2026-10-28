"""Source-admitted C APIs for selecting and resuming a bound call context."""

import re
from dataclasses import dataclass

import compile_facts
import php_src
from handler_index import Index
from php_src_c import Program, Source
from php_src_c.definitions import Definition
from php_src_c.source import STRING_PLACEHOLDER

CONTEXT_SOURCE = 'Zend/zend_fibers.c'
CONTEXT_DIGESTS = {
    'zend_fiber_init_context': '4d7234c5279e008b',
    'zend_fiber_resume_internal': '6bec028ec8783f49',
    'zend_fiber_switch_to': '75912fa52262fad1',
    'zend_fiber_switch_context': '9175f89d62121ec7',
    'zend_fiber_trampoline': 'c878a3d10a35d9fe',
}
CONSTRUCTOR_SOURCE = 'Zend/zend_object_handlers.c'
CONSTRUCTOR_DIGESTS = {'zend_std_get_constructor': '4268e1d0c9704f7e'}

OBJECT_SOURCE = 'Zend/zend_API.c'
OBJECT_DIGESTS = {
    'object_init_ex': '869ba4546a6104d1',
    '_object_and_properties_init': '885f5a12b947db91',
}
INI_SOURCE = 'Zend/zend_ini.c'
TARGET_SOURCES = {
    'zend_call_function': 'Zend/zend_execute_API.c',
    'zend_call_known_function': 'Zend/zend_execute_API.c',
    'zend_call_known_fcc': 'Zend/zend_API.h',
}
# Expanded bodies also fence the macros used by these C API contracts.
EXPANSIONS = {
    CONTEXT_SOURCE: {
        'zend_fiber_init_context': 'b5f14d49d55b8c98',
        'zend_fiber_resume_internal': 'c80ea3541d58623a',
        'zend_fiber_switch_to': '3a56d2cb057cd9af',
        'zend_fiber_switch_context': 'dcc3a7ac180fbc91',
    },
    CONSTRUCTOR_SOURCE: {'zend_std_get_constructor': '21da37503dae06b7'},
    OBJECT_SOURCE: {
        'object_init_ex': '935d29b02100141a', '_object_and_properties_init': 'd875abe0c4f51110',
    },
    INI_SOURCE: {
        'zend_ini_long': '811ed7066c22b20f', 'zend_ini_string_ex': '29d2357019ceae9f',
        'zend_ini_str_ex': '25455a390e79eb34',
    },
    'Zend/zend_hash.h': {'zend_hash_str_find_ptr': '2d21d8aeb0fa92cb'},
    'Zend/zend_hash.c': {
        'zend_hash_str_find': '4b121dc365ab6d6c', 'zend_hash_str_find_bucket': '5c6775146be8ee32',
    },
    'Zend/zend_string.h': {
        'zend_inline_hash_func': '4b7aa6bbbff41817', 'zend_string_equals_cstr': '94b52ac22573c46e',
    },
}


def expansion_matches(index: Index, definition: Definition, digest: str) -> bool:
    text = index.pre.expand(definition.body, definition.source, index.disabled)
    text = STRING_PLACEHOLDER.sub(lambda match: repr(index.program.strings[int(match[1])]), text)
    return compile_facts.digest(text) == digest


def expansion_protocol(index: Index, path: str) -> bool:
    for name, digest in EXPANSIONS[path].items():
        found = [d for d in index.program.functions.get(name, ()) if not d.is_macro
                 and d.source.relative.as_posix() == path]
        if not found or not all(expansion_matches(index, d, digest) for d in found):
            return False
    return True


def source_protocol(program: Program, path: str, digests: dict[str, str]) -> bool:
    source = next((s for s in program.sources if s.relative.as_posix() == path), None)
    if source is None:
        return False
    text = php_src.strip_comments(source.path.read_text(encoding='utf-8'), path)
    text = re.sub(r'^\s*#[^\n]*', '', text, flags=re.M)
    try:
        return all(compile_facts.digest(compile_facts.function_text(text, name)) == digest
                   for name, digest in digests.items())
    except php_src.ExtractionFailure:
        return False


def constructor_protocol(program: Program) -> bool:
    header = next((s for s in program.sources if s.relative.as_posix() == 'Zend/zend_object_handlers.h'), None)
    return bool(header and re.search(r'zend_object_get_constructor_t\s+get_constructor\s*;', header.text)
                and re.search(r'typedef\s+zend_function\s*\*\s*\(\s*\*\s*zend_object_get_constructor_t\s*\)'
                              r'\s*\(\s*zend_object\s*\*\s*object\s*\)\s*;', header.text)
                and source_protocol(program, CONSTRUCTOR_SOURCE, CONSTRUCTOR_DIGESTS))


@dataclass(frozen=True)
class Protocols:
    contexts: bool
    constructors: bool
    objects: bool
    ini: bool


def read_protocols(index: Index) -> Protocols:
    program = index.program
    return Protocols(source_protocol(program, CONTEXT_SOURCE, CONTEXT_DIGESTS) and expansion_protocol(index, CONTEXT_SOURCE),
                     constructor_protocol(program) and expansion_protocol(index, CONSTRUCTOR_SOURCE),
                     source_protocol(program, OBJECT_SOURCE, OBJECT_DIGESTS) and expansion_protocol(index, OBJECT_SOURCE),
                     all(expansion_protocol(index, path) for path in
                         (INI_SOURCE, 'Zend/zend_hash.h', 'Zend/zend_hash.c', 'Zend/zend_string.h')))


def source_api(index: Index, call: tuple[str, Source], path: str) -> bool:
    name, source = call
    definitions = index.definitions(name, source)
    return bool(definitions) and all(d.source.relative.as_posix() == path for d in definitions)


def target_api(index: Index, call: tuple[str, Source]) -> bool:
    name, source = call
    definitions = index.definitions(name, source)
    return not definitions or all(d.source.relative.as_posix() == TARGET_SOURCES[name] for d in definitions)


def strlen_api(index: Index, source: Source) -> bool:
    if index.definitions('strlen', source) or index.definitions('_strlen', source):
        return False
    macro = index.pre.lookup(source, 'strlen')
    if macro is None:
        return True
    params, body = macro
    return bool(params and len(params) == 1 and re.sub(r'\s+', '', body) == f'_strlen({params[0]})')
