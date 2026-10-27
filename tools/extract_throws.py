#!/usr/bin/env python3
"""Give the generated function and method entries the exception classes their php-src implementation may throw
(design-extraction.md, extract_throws.py; algorithm: spec-throws.md).

Reads every C source and header of one php-src checkout outside test
directories, maps each builtin function and method to its C handlers through
the ``*_arginfo.h`` function entry tables, and computes for every C function
and function-like macro a summary of the exception classes it may throw: a
fixpoint over the strongly connected components of the call graph, with
calls into argument binding, user code, diagnostics, and value conversion as
boundaries. Writes the ``throws`` line of every generated entry whose
handlers resolve to classes alone, every other line untouched; an entry whose
handlers throw an object the caller supplies keeps no line and is listed.
A second run over its own output changes nothing.
"""

import argparse
import collections
import re
import sys
from pathlib import Path

import php_src
import php_src_c
from php_src_c.definitions import UNKNOWN_ARGUMENT, Call, analyze, consistent, parameter_guard, strongly_connected
from php_src_c.source import IDENTIFIER, Source, split_arguments, strip_parentheses

TOOL = "tools/extract_throws.py"
CALLABLE_KINDS = ("function", "method")
THROWS_LINE = re.compile(r"^  throws: .*\n", re.M)
CAST = re.compile(r"^\(\s*(?:const\s+)?(?:struct\s+)?\w+\s*\**\s*\)\s*")

# Primitives that throw an instance of a class given as an argument: (class argument, class of NULL) (zend_exceptions.c).
CLASS_THROWS = {
    "zend_throw_exception_zstr": (0, "Exception"),
    "zend_throw_error": (0, "Error"),
    "zend_replace_error_handling": (1, "Exception"),
}
# zend_replace_error_handling converts later diagnostics into throws only in this mode (zend.c).
THROW_MODE = ("zend_replace_error_handling", 0, "EH_THROW")
# Primitives that throw an object given as an argument; NULL rethrows the pending exception (zend_exceptions.c).
OBJECT_THROWS = {"zend_throw_exception_object": 0, "zend_throw_exception_internal": 0}
# The primitive initializing a new object of a class into a zval: (object argument, class argument) (zend_API.c).
OBJECT_CREATION = ("object_init_ex", 0, 1)
# Argument binding: the parameter parsing API (zend_API.h).
BINDING_PREFIXES = (
    "ZEND_PARSE_PARAMETERS", "Z_PARAM_", "Z_FLF_PARAM_", "zend_parse_arg", "zend_parse_parameters",
    "zend_parse_method_parameters", "zend_wrong_parameter", "zend_wrong_callback",
)
# Binding specifiers that check a value beyond its declared type, and the class they throw (zend_API.h).
SPECIFIER_MACROS = (("Z_PARAM_PATH", "ValueError"), ("Z_PARAM_CLASS", "TypeError"))
FORMAT_SPECIFIERS = {"p": "ValueError", "P": "ValueError", "C": "TypeError"}
# The format string argument of each parsing function (zend_API.h).
FORMAT_ARGUMENT = {"zend_parse_parameters": 1, "zend_parse_parameters_ex": 2, "zend_parse_method_parameters": 2}
# The calls that run user code: the executor, functions, constant expressions, generators, and fibers (zend_execute.h,
# zend_execute_API.c, zend_ast.h, zend_generators.c, zend_fibers.c).
USER_CODE = {
    "execute_ex", "zend_execute", "zend_call_function", "zend_ast_evaluate_ex", "zend_generator_resume",
    "zend_fiber_switch_context", "zend_fiber_delegate_transfer_result",
}
# Diagnostics; a throw they cause under EH_THROW is attributed to zend_replace_error_handling (zend.c, main.c).
DIAGNOSTIC_PREFIXES = ("zend_error", "php_error_docref")
DIAGNOSTICS = {"php_verror"}
# Value conversion: the conversion API zend_operators.h declares, matched by these prefixes, and the truth tests.
CONVERSION_HEADER = Path("Zend/zend_operators.h")
CONVERSION_PREFIXES = ("convert_", "_convert_", "_try_convert_", "try_convert_", "zval_get_", "zval_try_get_",
                       "_zval_get_", "_zval_try_get_")
TRUTH_TESTS = {"zend_is_true", "zend_object_is_true", "i_zend_is_true", "zval_is_true"}
TRUE_LITERALS, FALSE_LITERALS = {"true", "1"}, {"false", "0", "NULL", "nullptr"}
NULL_LITERALS = {"NULL", "nullptr", "0"}
OBJECT_ACCESSORS = re.compile(r"^(?:Z_OBJ_P|Z_OBJ)\s*\((.*)\)$", re.S)
CLASS_OF_OBJECT = re.compile(r"^(?:Z_OBJCE_P|Z_OBJCE)\s*\((.*)\)$", re.S)

# Summary element kinds (spec-throws.md): an object no class set bounds is open; a class expression no rule resolves is
# unresolved, and fails the run when it reaches an entry.
CLASS, CLASS_PARAM, OBJECT_PARAM, OPEN, UNRESOLVED = "class", "class_param", "object_param", "open", "unresolved"
# The argument expression of a function reference, whose call site is not in the body; it resolves to no class.
UNKNOWN_ARGUMENT = "__ARGUMENT__"
# A function named as a value; an operand of an equality test is compared, never passed on to be called.

class Program(php_src_c.Program):
    """The shared reader's program with the conversion names of the throws boundary."""

    def __init__(self, root):
        super().__init__(root)
        self.conversions = conversion_names(root / CONVERSION_HEADER, self.strings)


def conversion_names(header, strings):
    text = Source(header, strings).text + "\n".join(f"{n}()" for n, _, _ in Source(header, strings).macros)
    return {n for n in IDENTIFIER.findall(text) if n.startswith(CONVERSION_PREFIXES)} | TRUTH_TESTS


class Summary:
    """What one definition may throw, which classes it creates into its parameters, and which classes it returns."""

    def __init__(self, throws=frozenset(), creates=None, returns=frozenset()):
        self.throws, self.creates, self.returns = throws, creates or {}, returns

    def __eq__(self, other):
        return (self.throws, self.creates, self.returns) == (other.throws, other.creates, other.returns)


EMPTY = Summary()


def element(kind, value, guards=frozenset()):
    return kind, value, guards


class Evaluation:
    """One pass over one definition under the current summaries of its callees."""

    def __init__(self, program, definition, summaries):
        self.program, self.definition, self.summaries = program, definition, summaries
        self.creations, self.creates = collections.defaultdict(set), collections.defaultdict(set)

    def run(self):
        for call in self.definition.calls:
            self.create(call)
        throws = {t for call in self.definition.calls for t in self.throws(call)}
        returns = set()
        if self.definition.returns_class:
            for expression in self.definition.returns:
                returns |= self.class_elements(expression, None)
        return Summary(frozenset(throws), {k: frozenset(v) for k, v in self.creates.items()}, frozenset(returns))

    def callees(self, call):
        return self.program.resolve(self.definition, call)

    def create(self, call):
        """Record the objects a call initializes: by object_init_ex or by a callee creating into a parameter."""
        name, target_index, class_index = OBJECT_CREATION
        if call.args is None:
            return
        if call.name == name:
            self.created(call.argument(target_index, "NULL"), self.class_elements(call.argument(class_index, "NULL"), None))
            return
        if self.is_boundary(call.name):
            return
        for callee in self.callees(call):
            for index, classes in self.summaries.get(id(callee), EMPTY).creates.items():
                if index < len(call.args):
                    self.created(call.args[index], {c for t in classes for c in self.instantiate_class(t, call)})

    def created(self, target, classes):
        variable = object_variable(target)
        index = self.definition.index(variable)
        (self.creates[index] if index is not None else self.creations[variable]).update(classes)

    def is_boundary(self, name):
        return (
            name.startswith(BINDING_PREFIXES) or name in USER_CODE or name in DIAGNOSTICS
            or name.startswith(DIAGNOSTIC_PREFIXES) or name in self.program.conversions
            or name in CLASS_THROWS or name in OBJECT_THROWS or name == OBJECT_CREATION[0]
        )

    def throws(self, call):
        name, guards = call.name, call.guards
        if name in CLASS_THROWS:
            if name == THROW_MODE[0] and call.argument(THROW_MODE[1], "") != THROW_MODE[2]:
                return set()
            index, default = CLASS_THROWS[name]
            return {guarded(t, guards) for t in self.class_elements(call.argument(index, "NULL"), default)}
        if name in OBJECT_THROWS:
            return {guarded(t, guards) for t in self.object_elements(call.argument(OBJECT_THROWS[name], "NULL"))}
        if self.is_boundary(name):
            return {element(CLASS, c, guards) for c in self.specifier_classes(call)}
        found = set()
        for callee in self.callees(call):
            for raised in self.summaries.get(id(callee), EMPTY).throws:
                found |= self.instantiate_raise(raised, call)
        return found

    def specifier_classes(self, call):
        """The classes a binding specifier throws for a value its declared type admits."""
        classes = {cls for prefix, cls in SPECIFIER_MACROS if call.name.startswith(prefix)}
        index = FORMAT_ARGUMENT.get(call.name)
        if index is not None:
            classes |= {FORMAT_SPECIFIERS[c] for c in self.program.string(call.argument(index, "")) if c in FORMAT_SPECIFIERS}
        return classes

    def instantiate_raise(self, raised, call):
        kind, value, callee_guards = raised
        guards = set(call.guards)
        for index, truth in callee_guards:
            argument = strip_parentheses(call.argument(index, ""))
            if argument in TRUE_LITERALS | FALSE_LITERALS:
                if (argument in TRUE_LITERALS) != truth:
                    return set()
                continue
            guard = parameter_guard(argument, self.definition.params)
            if guard:
                guards.add((guard[0], guard[1] == truth))
        if not consistent(guards):
            return set()
        if kind == CLASS_PARAM:
            index, default = value
            elements = self.class_elements(call.argument(index, "NULL"), default)
        elif kind == OBJECT_PARAM:
            elements = self.object_elements(call.argument(value, "NULL"))
        else:
            elements = {element(kind, value)}
        return {guarded(t, frozenset(guards)) for t in elements}

    def instantiate_class(self, class_term, call, seen=frozenset()):
        kind, value, _ = class_term
        if kind != CLASS_PARAM:
            return {class_term}
        index, default = value
        return self.class_elements(call.argument(index, "NULL"), default, seen)

    def class_elements(self, expression, default, seen=frozenset()):
        """The summary elements a class entry expression denotes."""
        expression = strip_casts(expression)
        if expression in seen:
            return set()
        if expression in NULL_LITERALS:
            return {element(CLASS, default)} if default else set()
        index = self.definition.index(expression)
        if index is not None:
            return {element(CLASS_PARAM, (index, default))}
        alternatives = conditional_alternatives(expression)
        if alternatives:
            return {t for e in alternatives for t in self.class_elements(e, default, seen)}
        of_object = CLASS_OF_OBJECT.match(expression)
        if of_object:
            return {t for t in self.object_elements(of_object.group(1)) if t[0] != OBJECT_PARAM} or {
                element(UNRESOLVED, f"{self.definition.name}: {expression}")
            }
        if expression in self.definition.assignments:
            return {t for rhs in self.definition.assignments[expression] for t in self.class_elements(rhs, default, seen | {expression})}
        if expression in self.program.class_entries:
            return {element(CLASS, self.program.class_entries[expression])}
        call = re.match(r"^([A-Za-z_]\w*)\s*\((.*)\)$", expression, re.S)
        inner = call and Call(call.group(1), split_arguments(call.group(2)), frozenset())
        if inner and self.callees(inner):
            return {c for callee in self.callees(inner) for t in self.summaries.get(id(callee), EMPTY).returns for c in self.instantiate_class(t, inner, seen | {expression})}
        return {element(UNRESOLVED, f"{self.definition.name}: {expression}")}

    def object_elements(self, expression):
        """The summary elements an object expression denotes: created classes, a caller's object, or an object no analysis bounds."""
        variable = object_variable(expression)
        if variable in NULL_LITERALS:
            return set()
        if variable in self.creations:
            return set(self.creations[variable])
        index = self.definition.index(variable)
        if index is not None:
            return {element(OBJECT_PARAM, index)}
        return {element(OPEN, f"object {variable}")}


def guarded(found, guards):
    kind, value, own = found
    return kind, value, own | guards


def strip_casts(expression):
    expression = strip_parentheses(expression)
    while CAST.match(expression):
        expression = strip_parentheses(CAST.sub("", expression, count=1))
    return expression


def object_variable(expression):
    expression = strip_casts(expression).lstrip("&").strip()
    accessor = OBJECT_ACCESSORS.match(expression)
    return object_variable(accessor.group(1)) if accessor else strip_casts(expression)


def conditional_alternatives(expression):
    """The two alternatives of a top-level conditional expression, or None."""
    depth, question = 0, None
    for j, ch in enumerate(expression):
        depth += (ch in "([{") - (ch in ")]}")
        if depth == 0 and ch == "?" and question is None:
            question = j
        elif depth == 0 and ch == ":" and question is not None:
            return expression[question + 1:j], expression[j + 1:]
    return None

def summarize(program, roots):
    """The fixpoint summary of every definition reachable from the roots."""
    definitions, edges, frontier = {}, {}, list(roots)
    while frontier:
        definition = frontier.pop()
        if id(definition) in definitions:
            continue
        definitions[id(definition)] = definition
        analyze(definition, program.functions)
        callees = [c for call in definition.calls for c in program.resolve(definition, call)]
        edges[id(definition)] = [id(c) for c in callees]
        frontier.extend(callees)
    summaries = {}
    for component in strongly_connected(list(definitions), edges):
        changed = True
        while changed:
            changed = False
            for node in component:
                summary = Evaluation(program, definitions[node], summaries).run()
                if summary != summaries.get(node, EMPTY):
                    summaries[node] = summary
                    changed = True
    return summaries


def handler_definitions(program, entries):
    """Handler name → its definitions; a Handler no definition defines fails the run."""
    handlers = {h: program.functions.get(h, []) for names in entries.values() for h in names}
    undefined = sorted(h for h, found in handlers.items() if not found)
    if undefined:
        raise php_src.ExtractionFailure(f"Handlers no definition defines: {', '.join(undefined)}")
    return handlers


def throws_of(program, entries):
    """(kind, folded subject) → the sorted folded classes its Handlers may throw, or None when one throws an object
    no class set bounds, for every entry with a Handler; a class expression no rule resolves fails the run."""
    handlers = handler_definitions(program, entries)
    summaries = summarize(program, [d for found in handlers.values() for d in found])
    result, unresolved = {}, set()
    for key, names in entries.items():
        if not names:
            continue
        elements = {t for h in names for d in handlers[h] for t in summaries.get(id(d), EMPTY).throws}
        unresolved |= {f"{t[0]} {t[1]}" for t in elements if t[0] not in (CLASS, OPEN)}
        result[key] = None if any(t[0] == OPEN for t in elements) else sorted({t[1].lower() for t in elements})
    if unresolved:
        raise php_src.ExtractionFailure(f"class expressions no rule resolves reach an entry: {'; '.join(sorted(unresolved))}")
    return result


def check_declared(models, throws):
    """Fail when a throws element names a class no generated document declares."""
    classes = php_src.declared(php_src.generated_documents(models))
    undeclared = sorted({c for found in throws.values() if found for c in found if ("class", c) not in classes})
    if undeclared:
        raise php_src.ExtractionFailure(f"throws elements no generated document declares: {', '.join(undeclared)}")


def with_throws(entry, throws):
    """The entry text with its throws line replaced: the classes of its Handlers, or none."""
    text = THROWS_LINE.sub("", entry.text)
    found = throws.get(entry.key()) if entry.kind in CALLABLE_KINDS else None
    return text if found is None else text + f"  throws: [{', '.join(found)}]\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--php-src", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    try:
        program = Program(args.php_src)
        throws = throws_of(program, program.entries())
        check_declared(args.models, throws)
        changed = php_src.rewrite(args.models, lambda entry: with_throws(entry, throws))
    except php_src.ExtractionFailure as failure:
        print(f"{TOOL}: {failure}", file=sys.stderr)
        sys.exit(1)
    opened = sorted(subject for (_, subject), found in throws.items() if found is None)
    print(
        f"{TOOL}: {len(throws)} entries with a Handler, {changed} documents rewritten; "
        f"no throws line (an object the caller supplies): {', '.join(opened)}; "
        f"method tables no class registration names: {', '.join(sorted(program.unowned))}"
    )


if __name__ == "__main__":
    main()