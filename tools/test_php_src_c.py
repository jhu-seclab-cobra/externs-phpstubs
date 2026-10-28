"""Tests for php_src_c: the shared C reader of the php-src producers (design-extraction-handlers.md).

Run: python3 -B -m unittest discover -s tools -p "test_*.py" (from the externs-phpstubs root).
- conditional compilation: the plain view keeps every branch text and drops the directives; the provenance view
  keeps one marker per branch with the condition it stands under
- linkage: a static definition is visible to its own file only; a header definition to every file
- macros: a function-defining macro invocation is expanded; handler macros stay unexpanded
- registrations: the class a register_class function registers, its kind, its flags and its parent
- parameter types: the type name of a parameter declaration and of each parameter of a definition
- expressions: sizeof keeps the words of its operand, a C++ cast reads as the C cast, a scoped name is one name,
  a parenthesized type name before an operand is a cast whatever the type is called, a function prototype
  inside a body declares nothing
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import php_src
from php_src_c import Program, Source
from php_src_c.definitions import ParseFailure, definitions_of, parse_body, parse_expression
from php_src_c.registrations import Registration
from php_src_c.source import BRANCH, matching, parameter_type, split_arguments

CONDITIONAL = """int always;
#ifdef HAVE_A
int a;
#else
int b;
#endif
#ifndef HAVE_C
int c;
#elif defined(HAVE_D)
int d;
#endif
"""

REGISTRATIONS = """
static zend_class_entry *register_class_Plain(void)
{
	zend_class_entry ce, *class_entry;

	INIT_CLASS_ENTRY(ce, "Plain", class_Plain_methods);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);

	return class_entry;
}
static zend_class_entry *register_class_Sealed(zend_class_entry *class_entry_Plain, zend_class_entry *class_entry_Iface)
{
	zend_class_entry ce, *class_entry;

	INIT_NS_CLASS_ENTRY(ce, "Ns", "Sealed", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, class_entry_Plain, ZEND_ACC_FINAL|ZEND_ACC_NOT_SERIALIZABLE);
	zend_class_implements(class_entry, 1, class_entry_Iface);

	return class_entry;
}
static zend_class_entry *register_class_Legacy(zend_class_entry *class_entry_Plain)
{
	zend_class_entry ce, *class_entry;

	INIT_CLASS_ENTRY(ce, "Legacy", NULL);
	class_entry = zend_register_internal_class_ex(&ce, class_entry_Plain);

	return class_entry;
}
static zend_class_entry *register_class_Iface(void)
{
	zend_class_entry ce, *class_entry;

	INIT_CLASS_ENTRY(ce, "Iface", NULL);
	class_entry = zend_register_internal_interface(&ce);

	return class_entry;
}
static zend_class_entry *register_class_Mode(zend_class_entry *class_entry_UnitEnum)
{
	zend_class_entry *class_entry = zend_register_internal_enum("Mode", IS_UNDEF, NULL);
	zend_class_implements(class_entry, 1, class_entry_UnitEnum);

	return class_entry;
}
static zend_class_entry *register_class_Helper(void)
{
	zend_class_entry ce, *class_entry;

	INIT_CLASS_ENTRY(ce, "Helper", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, ZEND_ACC_TRAIT);

	return class_entry;
}
"""

LINKAGE_ONE = """
static int shared(void) { return 1; }
int visible(void) { return shared(); }
"""

LINKAGE_TWO = """
static int shared(void) { return 2; }
int other(void) { return shared(); }
"""

MACRO_FILE = """
#define DEFINE_GETTER(name, value) static int name(void) { return value; }
DEFINE_GETTER(get_seven, 7)
ZEND_FUNCTION(zif_target)
{
	return;
}
"""


def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class SourceTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_plain_view_keeps_every_branch_and_drops_directives(self):
        source = Source(write(self.root, "c.c", CONDITIONAL), [])
        for text in ("int a;", "int b;", "int c;", "int d;"):
            self.assertIn(text, source.text)
        self.assertNotIn("#", source.text)
        self.assertNotIn("__BRANCH", source.text)

    def test_provenance_view_marks_each_branch_with_its_condition(self):
        source = Source(write(self.root, "c.c", CONDITIONAL), [], provenance=True)
        expected = {
            "a": "defined(HAVE_A)",
            "b": "!(defined(HAVE_A))",
            "c": "!defined(HAVE_C)",
            "d": "defined(HAVE_D)",
        }
        for name, condition in expected.items():
            before = source.text[: source.text.index(f"int {name};")]
            group, branch = BRANCH.findall(before)[-1]
            self.assertEqual(condition, source.conditions[(int(group), int(branch))])
        self.assertEqual([("0", "END")], BRANCH.findall(source.text)[2:3])

    def test_provenance_view_adds_markers_only(self):
        plain = Source(write(self.root, "c.c", CONDITIONAL), [])
        marked = Source(self.root / "c.c", [], provenance=True)
        self.assertEqual(plain.text, BRANCH.sub("", marked.text))
        self.assertEqual(plain.macros, marked.macros)

    def test_helpers_split_arguments_and_match_brackets(self):
        self.assertEqual(["a", "f(b, c)", "{d, e}"], split_arguments("a, f(b, c), {d, e}"))
        self.assertEqual(6, matching("f(a(b))", 1))


class ProgramTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_static_definition_resolves_in_its_own_file(self):
        write(self.root, "ext/a/one.c", LINKAGE_ONE)
        write(self.root, "ext/a/two.c", LINKAGE_TWO)
        write(self.root, "Zend/zend_operators.h", "")
        program = Program(self.root)
        callers = {d.name: d for d in program.functions["visible"] + program.functions["other"]}
        for name, expected in (("visible", "ext/a/one.c"), ("other", "ext/a/two.c")):
            call = [c for c in definitions_calls(program, callers[name]) if c.name == "shared"][0]
            found = program.resolve(callers[name], call)
            self.assertEqual([Path(expected)], [d.source.relative for d in found])

    def test_function_defining_macro_is_expanded(self):
        write(self.root, "ext/a/m.c", MACRO_FILE)
        write(self.root, "Zend/zend_operators.h", "")
        program = Program(self.root)
        self.assertIn("get_seven", program.functions)
        self.assertEqual(["zif_zif_target"], [d.name for d in program.functions["zif_zif_target"]])

    def test_definitions_of_reports_an_unbalanced_brace(self):
        source = Source(write(self.root, "bad.c", "int f(void) {\n"), [])
        source.relative = Path("bad.c")
        with self.assertRaisesRegex(php_src.ExtractionFailure, "bad.c: unbalanced brace"):
            list(definitions_of(source))

    def test_registrations_record_name_kind_flags_and_parent(self):
        write(self.root, "ext/a/a_arginfo.h", REGISTRATIONS)
        write(self.root, "Zend/zend_operators.h", "")
        program = Program(self.root)
        registered = program.registrations
        self.assertEqual({"plain", "ns\\sealed", "legacy", "iface", "mode", "helper"}, set(registered))
        plain, sealed = registered["plain"], registered["ns\\sealed"]
        self.assertIsInstance(plain, Registration)
        self.assertEqual(("Plain", "class", frozenset(), None), (plain.name, plain.kind, plain.flags, plain.parent))
        self.assertEqual("Ns\\Sealed", sealed.name)
        self.assertEqual(frozenset({"ZEND_ACC_FINAL", "ZEND_ACC_NOT_SERIALIZABLE"}), sealed.flags)
        self.assertEqual("class_entry_Plain", sealed.parent)
        self.assertEqual("register_class_Sealed", sealed.function)
        self.assertEqual(Path("ext/a/a_arginfo.h"), sealed.source)
        self.assertEqual(frozenset(), registered["legacy"].flags)
        self.assertEqual("class_entry_Plain", registered["legacy"].parent)
        self.assertEqual("interface", registered["iface"].kind)
        self.assertEqual("enum", registered["mode"].kind)
        self.assertEqual("trait", registered["helper"].kind)

    def test_class_names_and_entries_keep_their_throws_view(self):
        write(self.root, "ext/a/a_arginfo.h", REGISTRATIONS)
        write(self.root, "ext/a/a.c", "void init(void) { a_ce = register_class_Plain(); }\n")
        write(self.root, "Zend/zend_operators.h", "")
        program = Program(self.root)
        self.assertEqual("Plain", program.class_names["register_class_Plain"])
        self.assertEqual({"a_ce": "Plain"}, program.class_entries)

    def test_duplicate_registered_name_fails(self):
        plain = REGISTRATIONS.split("static zend_class_entry *register_class_Sealed")[0]
        write(self.root, "ext/a/a_arginfo.h", REGISTRATIONS)
        write(self.root, "ext/b/b_arginfo.h", plain.replace("register_class_Plain", "register_class_PlainTwo"))
        write(self.root, "Zend/zend_operators.h", "")
        with self.assertRaisesRegex(php_src.ExtractionFailure, "plain: registered by"):
            Program(self.root)


def definitions_calls(program, definition):
    from php_src_c.definitions import analyze

    analyze(definition, program.functions)
    return definition.calls


if __name__ == "__main__":
    unittest.main()


class BodyParserTest(unittest.TestCase):
    def test_statements_parse_to_nodes(self):
        block = parse_body("{ int a = 1; if (a) { b = 2; } else c = 3; return a ? b : c; }", [])
        kinds = [node[0] for node in block[1]]
        self.assertEqual(["decl", "if", "return"], kinds)
        self.assertEqual(("cond", ("name", "a"), ("name", "b"), ("name", "c")), block[1][2][1])

    def test_conditional_group_keeps_each_branch(self):
        block = parse_body("{\n__BRANCH_1_1__\n x = 1;\n__BRANCH_1_2__\n x = 2;\n__BRANCH_1_END__\n return x; }", [])
        group = block[1][0]
        self.assertEqual("cgroup", group[0])
        self.assertEqual([1, 2], [number for number, _ in group[2]])

    def test_expression_forms(self):
        call = parse_expression("f(a, &b->c[2], (int)d)")
        self.assertEqual("call", call[0])
        self.assertEqual(["name", "un", "cast"], [argument[0] for argument in call[2]])

    def test_initializer_items_carry_designators_and_branch_marks(self):
        block = parse_body("{ T t = { .a = 1, 2 }; }", [])
        init = block[1][0][2][0][3]
        self.assertEqual("init", init[0])
        self.assertEqual(2, len(init[1]))
        self.assertEqual(3, len(init[1][0]))

    def test_parenthesized_star_fails_as_a_parse_error(self):
        with self.assertRaises(ParseFailure):
            parse_expression("(*) + 1")

    def test_sizeof_keeps_the_words_of_its_operand(self):
        self.assertEqual(("sizeof", ("struct", "box")), parse_expression("sizeof(struct box)"))
        self.assertEqual(("sizeof", ()), parse_expression("sizeof value"))

    def test_cxx_cast_reads_as_the_c_cast(self):
        self.assertEqual(parse_expression("(box *)p"), parse_expression("reinterpret_cast<box *>(p)"))
        self.assertEqual(parse_expression("(int)(a + b)"), parse_expression("static_cast<int>(a + b)"))

    def test_scoped_name_is_one_name(self):
        self.assertEqual(("call", ("name", "std::isfinite"), [("name", "d")]), parse_expression("std::isfinite(d)"))
        self.assertEqual(("cond", ("name", "a"), ("name", "b"), ("name", "c")), parse_expression("a ? b : c"))

    def test_parenthesized_type_before_an_operand_is_a_cast(self):
        self.assertEqual(("cast", ("gmp_ulong",), ("name", "shift")), parse_expression("(gmp_ulong) shift"))
        self.assertEqual(("cast", ("gmp_ulong",), ("num", 3)), parse_expression("(gmp_ulong) 3"))

    def test_prototype_in_a_body_declares_no_variable(self):
        block = parse_body("{ STDAPI VarCmp(LPVARIANT left, DWORD flags); return VarCmp(a, 0); }")
        self.assertEqual([("decl", ("STDAPI",), []), "return"], [block[1][0], block[1][1][0]])

    def test_call_statement_is_not_a_prototype(self):
        block = parse_body("{ lookup(table, key); }")
        self.assertEqual("expr", block[1][0][0])

    def test_parenthesized_variable_before_an_operator_is_not_a_cast(self):
        self.assertEqual("bin", parse_expression("(limit) - 1", ["limit"])[0])
        self.assertEqual("bin", parse_expression("(limit) * count", ["limit"])[0])


class ParameterTypeTest(unittest.TestCase):
    def test_declaration_names_its_type(self):
        self.assertEqual("zend_object", parameter_type("zend_object *object"))
        self.assertEqual("box", parameter_type("const struct box *const items[4]"))
        self.assertEqual("long", parameter_type("unsigned long count"))

    def test_declaration_without_a_name_has_no_type(self):
        self.assertIsNone(parameter_type("void"))

    def test_definition_records_the_type_of_each_parameter(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Source(write(Path(directory), "f.c", "int f(zend_object *object, struct box b, int n) { return 0; }\n"), [])
            source.relative = Path("f.c")
            definition = next(iter(definitions_of(source)))
        self.assertEqual({"object": "zend_object", "b": "box", "n": "int"}, definition.param_types)
