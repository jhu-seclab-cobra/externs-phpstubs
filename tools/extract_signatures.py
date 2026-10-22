#!/usr/bin/env python3
"""Give the generated function and method entries their php-src signatures (design-extraction.md, extract_signatures.py).

Reads every function and method declaration of the php-src stubs: parameter
names, declared types, defaults, by-reference and variadic marks, and the
declared return type, with class names resolved by PHP's name resolution
rules. Also gives each function the `opcodeArities` php-src fixes: the
argument counts at which the engine compiles a call to one opcode. Rewrites
the subject line and signature of every generated function and method entry
php-src declares, removes the propagation statements naming
an argument position the signature lacks, every other line untouched. Each
such entry lives in the generated document of its php-src extension, moved
there when another document holds it, and each declaration no models
document declares is added: a function to the generated document of its
extension, a method to the generated document declaring its class. A second run over its own output changes nothing.
"""

import argparse
import re
import sys
from pathlib import Path

import php_src

TOOL = "tools/extract_signatures.py"

# PHP reads an omitted parameter or return type as mixed; the model format requires one.
ABSENT_TYPE = "mixed"
# Type names PHP never resolves against a namespace.
RELATIVE_TYPES = {
    "self", "static", "parent", "string", "int", "float", "bool", "true", "false", "array", "object",
    "callable", "iterable", "resource", "mixed", "void", "never", "null",
}
# Plain scalars a YAML 1.1 reader resolves to a non-string; written quoted.
YAML_RESERVED = re.compile(r"^(?:y|n|yes|no|true|false|on|off|null|~|[-+]?[0-9][0-9_.:]*)$", re.I)

CLASS_DECLARATION = re.compile(r"\b(?:class|interface|enum|trait)\s+(\w+)[^{;]*\{")
FUNCTION = re.compile(r"\bfunction\s+&?\s*(\w+)\s*\(")
DOC_COMMENT = re.compile(r"/\*\*(.*?)\*/", re.S)
# What separates a doc comment from its function keyword once comments and attributes are blanked.
DECLARATION_HEAD = re.compile(r"\s*(?:(?:public|protected|private|static|final|abstract)\s+)*(?=function\b)")
PREFER_REF = re.compile(r"@prefer-ref\s+\$(\w+)")
FRAMELESS_ARITY = re.compile(r'@frameless-function\s*\{\s*"arity"\s*:\s*(\d+)\s*\}')
# The compiler's by-name dispatch of function calls compiled to one opcode, and the operands such a compile function takes.
SPECIAL_COMPILER = "Zend/zend_compile.c"
SPECIAL_DISPATCH = re.compile(r"\breturn\s+(zend_compile_func_\w+)\(")
DISPATCHED_NAME = re.compile(r'\blcname,\s*"(\w+)"')
OPERAND_ARGUMENT = re.compile(r"\bzend_compile_expr\(\s*&\w+\s*,\s*args->child\[(\d+)\]\s*\)")
ARGUMENT_COUNT_CHECK = re.compile(r"\bargs->children\s*!=\s*(\d+)")
RETURN_TYPE = re.compile(r"\s*(?::\s*([^{;]+?))?\s*[{;]")
PARAMETER = re.compile(
    r"^(?:(?:public|protected|private|readonly)\s+)*(?P<type>.*?)\s*(?P<ref>&)?\s*(?P<variadic>\.\.\.)?\s*"
    r"\$(?P<name>\w+)\s*(?P<default>=.*)?$",
    re.S,
)
TYPE_NAME = re.compile(r"\\?[A-Za-z_][\w\\]*")
# One propagation statement of an entry, and an argument port it names.
STATEMENT = re.compile(r"^  - from: (\S+)\n    to: (\S+)\n", re.M)
ARGUMENT_PORT = re.compile(r"^argument\((\d+)\)$")


class Parameter:
    def __init__(self, name, type_, optional, by_ref, variadic):
        self.name, self.type, self.optional, self.by_ref, self.variadic = name, type_, optional, by_ref, variadic

    def render(self):
        lines = [f"    - name: {scalar(self.name)}", f"      type: {scalar(self.type)}"]
        lines += ["      optional: true"] * self.optional + ["      byRef: true"] * self.by_ref
        lines += ["      variadic: true"] * self.variadic
        return lines


class Signature:
    """One callable declaration: subject kind, spelled subject, parameters, return type, and its stub."""

    def __init__(self, kind, subject, params, return_type, source, opcode_arities=()):
        self.kind, self.subject, self.params, self.return_type, self.source = kind, subject, params, return_type, source
        self.opcode_arities = sorted(set(opcode_arities))

    def subsumes(self, other):
        """True when every call other admits this one admits, with a return type including other's."""
        shared = len(other.params)
        return (
            len(self.params) >= shared
            and [p.render() for p in self.params[:shared]] == [p.render() for p in other.params]
            and all(p.optional for p in self.params[shared:])
            and union_members(other.return_type) <= union_members(self.return_type)
        )

    def has_port(self, port):
        """False for an argument position beyond a parameter list without a variadic parameter."""
        argument = ARGUMENT_PORT.match(port)
        if argument is None or any(p.variadic for p in self.params):
            return True
        return int(argument.group(1)) < len(self.params)

    def admitted(self, sections):
        """The sections without the propagation statements naming a port this signature lacks."""
        kept = STATEMENT.sub(lambda m: m.group(0) if all(map(self.has_port, m.groups())) else "", sections)
        if "  propagation:\n" in kept and not STATEMENT.search(kept):
            raise php_src.ExtractionFailure(f"{self.subject}: no propagation statement names a declared port")
        return kept

    def render(self):
        lines = ["- subject:", f"    {self.kind}: {self.subject}", "  signature:"]
        if self.params:
            lines.append("    params:")
            lines += [line for p in self.params for line in p.render()]
        lines.append(f"    returnType: {scalar(self.return_type)}")
        if self.opcode_arities:
            lines.append(f"    opcodeArities: [{', '.join(map(str, self.opcode_arities))}]")
        return "\n".join(lines) + "\n"


def scalar(value):
    """Spell a string as a YAML plain scalar, quoted when a YAML 1.1 reader would read another type."""
    return f"'{value}'" if YAML_RESERVED.match(value) else value


def union_members(type_):
    return {type_[1:].lower(), "null"} if type_.startswith("?") else set(type_.lower().split("|"))


def declared_type(spelled, stub, offset):
    text = re.sub(r"\s+", "", spelled or "")
    if not text:
        return ABSENT_TYPE

    def resolved(match):
        name = match.group(0)
        return name if name.lower() in RELATIVE_TYPES else stub.resolve(name, offset)

    return TYPE_NAME.sub(resolved, text)


def parameter(text, stub, offset, prefer_ref):
    match = PARAMETER.match(text)
    if not match:
        raise php_src.ExtractionFailure(f"{stub.source}: unreadable parameter {text!r}")
    variadic = bool(match.group("variadic"))
    return Parameter(
        match.group("name"),
        declared_type(match.group("type"), stub, offset),
        variadic or bool(match.group("default")),
        bool(match.group("ref")) or match.group("name") in prefer_ref,
        variadic,
    )


def prefer_ref_names(stub):
    """The function keyword offset → parameter names its doc comment tags `@prefer-ref`."""
    tagged = {}
    for comment in DOC_COMMENT.finditer(stub.raw):
        head = DECLARATION_HEAD.match(stub.text, comment.end())
        if head:
            tagged[head.end()] = set(PREFER_REF.findall(comment.group(1)))
    return tagged


def frameless_arities(stub):
    """The function keyword offset → argument counts its doc comment tags `@frameless-function`."""
    tagged = {}
    for comment in DOC_COMMENT.finditer(stub.raw):
        head = DECLARATION_HEAD.match(stub.text, comment.end())
        if head:
            tagged[head.end()] = {int(n) for n in FRAMELESS_ARITY.findall(comment.group(1))}
    return tagged


def special_function_arities(root):
    """Function name → the argument count the compiler's by-name dispatch compiles to one opcode, for the dispatched
    functions whose compile function takes two or more arguments as operands. Fewer operands leave the order of
    evaluation among the arguments no question, and the compile function names the count it accepts."""
    path = root / SPECIAL_COMPILER
    text = php_src.strip_comments(path.read_text(encoding="utf-8"), SPECIAL_COMPILER)
    chain = re.search(r"\bstatic\s+zend_result\s+zend_try_compile_special_func_ex\([^)]*\)\s*{", text)
    if chain is None:
        raise php_src.ExtractionFailure(f"{SPECIAL_COMPILER}: no zend_try_compile_special_func_ex")
    end = php_src.matching(text, chain.end() - 1, SPECIAL_COMPILER)
    arities, previous = {}, chain.end()
    for dispatch in SPECIAL_DISPATCH.finditer(text, chain.end(), end):
        names = DISPATCHED_NAME.findall(text[previous : dispatch.start()])
        previous = dispatch.end()
        definition = re.search(rf"\bstatic\s+zend_result\s+{dispatch.group(1)}\([^)]*\)\s*{{", text)
        if definition is None:
            raise php_src.ExtractionFailure(f"{SPECIAL_COMPILER}: no definition of {dispatch.group(1)}")
        body = text[definition.end() - 1 : php_src.matching(text, definition.end() - 1, SPECIAL_COMPILER)]
        operands = set(OPERAND_ARGUMENT.findall(body))
        if len(operands) < 2:
            continue
        checks = set(ARGUMENT_COUNT_CHECK.findall(body))
        if checks != {str(len(operands))}:
            raise php_src.ExtractionFailure(f"{dispatch.group(1)}: operands {sorted(operands)} against argument count checks {sorted(checks)}")
        arities.update({name: len(operands) for name in names})
    return arities


def class_bodies(stub):
    """The (start, end, resolved class name) span of every class-like body."""
    spans = []
    for match in CLASS_DECLARATION.finditer(stub.text):
        open_brace = match.end() - 1
        close = php_src.matching(stub.text, open_brace, stub.source)
        spans.append((open_brace, close, stub.resolve(match.group(1), match.start())))
    return spans


def read_stub(stub, special):
    """Yield the Signature of every function and method one stub declares; special is the function name → argument
    count the compiler compiles to one opcode."""
    bodies, prefer_ref, frameless = class_bodies(stub), prefer_ref_names(stub), frameless_arities(stub)
    for match in FUNCTION.finditer(stub.text):
        offset, close = match.start(), php_src.matching(stub.text, match.end() - 1, stub.source)
        refs = prefer_ref.get(offset, set())
        params = [parameter(p, stub, offset, refs) for p in php_src.split_top_level(stub.text[match.end() : close])]
        returned = RETURN_TYPE.match(stub.text, close + 1)
        if not returned:
            raise php_src.ExtractionFailure(f"{stub.source}: unreadable return type of {match.group(1)}")
        return_type = declared_type(returned.group(1), stub, offset)
        owner = next((name for start, end, name in bodies if start < offset < end), None)
        if owner is None:
            name = php_src.resolve(match.group(1), stub.namespace_at(offset), {})
            arities = frameless.get(offset, set()) | ({special[name.lower()]} if name.lower() in special else set())
            yield Signature("function", name, params, return_type, stub.source, arities)
        else:
            yield Signature("method", f"{owner}::{match.group(1)}", params, return_type, stub.source)


def read_php_src(root):
    """Return the (kind, folded subject) → Signature map, one variant per subject by subsumption."""
    signatures, special = {}, special_function_arities(root)
    for stub in php_src.stubs(root):
        for signature in read_stub(stub, special):
            key = (signature.kind, signature.subject.lower())
            known = signatures.setdefault(key, signature)
            if known.subsumes(signature):
                continue
            if not signature.subsumes(known):
                raise php_src.ExtractionFailure(
                    f"{signature.subject}: neither {known.source} nor {signature.source} declares a signature subsuming the other"
                )
            signatures[key] = signature
    return signatures


def target_document(signature, models, class_documents):
    """The document a new declaration joins: its class's generated document, or its extension's."""
    if signature.kind == "function":
        return php_src.placement(models, php_src.extension_of(signature.source))
    owner = signature.subject.split("::")[0].lower()
    if ("class", owner) not in class_documents:
        raise php_src.ExtractionFailure(f"{signature.subject}: no generated document declares class {owner}")
    return class_documents[("class", owner)]


def relocate(models, signatures):
    """Move each generated callable entry php-src declares to the document of its php-src extension."""
    extensions = {key: php_src.extension_of(signature.source) for key, signature in signatures.items()}
    return php_src.relocate(models, extensions, TOOL)


def add_missing(models, signatures):
    """Add every php-src declaration no models document declares; return the number added."""
    known = php_src.declared(php_src.all_documents(models))
    class_documents = php_src.declared(php_src.generated_documents(models))
    additions = {}
    for key in sorted(signatures):
        if key in known:
            continue
        document = target_document(signatures[key], models, class_documents)
        additions.setdefault(document, []).append(signatures[key].render())
    for document, rendered in additions.items():
        php_src.append(document, rendered, TOOL)
    return sum(len(rendered) for rendered in additions.values())


def rewrite(models, signatures):
    """Rewrite the subject line and signature of each generated callable entry php-src declares."""

    def transform(entry):
        signature = signatures.get(entry.key())
        if signature is None:
            return entry.text
        return signature.render() + signature.admitted(entry.without_signature())

    return php_src.rewrite(models, transform)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--php-src", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    try:
        signatures = read_php_src(args.php_src)
        moved = relocate(args.models, signatures)
        added = add_missing(args.models, signatures)
        changed = rewrite(args.models, signatures)
    except php_src.ExtractionFailure as failure:
        print(f"{TOOL}: {failure}", file=sys.stderr)
        sys.exit(1)
    print(
        f"{TOOL}: {len(signatures)} php-src declarations, {moved} entries moved, {added} entries added, "
        f"{changed} documents rewritten"
    )


if __name__ == "__main__":
    main()
