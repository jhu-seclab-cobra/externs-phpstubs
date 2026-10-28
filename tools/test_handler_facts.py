"""Tests for the handler extraction (design-extraction-handlers.md, spec-extraction-handlers.md) over the small tree of
fixture_handler_tree.py.

Run: python3 -B -m unittest discover -s tools -p "test_*.py" (from the externs-phpstubs root).
- registration: classes registered, tables indexed from a declarator list, a table copied before a later slot write,
  slot writes read only in functions that name the table type, the parent's creator and table inherited
- creation: the creator's table of each class, the struct type it allocates, the default table of a class with no creator
- write sites: creation, copy, typed and foreign dispositions; a write that fits none fails the extraction
- request summaries: result kinds per cast and operation request, a compare that may return, string dispatch order,
  conditional slots as two table alternatives, absent slots, the rendered handlers field
"""

import collections
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import fixture_handler_tree
import php_src
from handler_create import Creation
from handler_facts import effective_string_method, read_handler_tables
from handler_memory import Fn, Ptr
from handler_minit import Registered
from handler_render import Table, render_handlers
from handler_sites import Sites, typed_tables
from handler_summary import SummaryPolicy
from php_src_c import Program

DEMO = "ext/demo/demo.c"
STD = "Zend/zend_object_handlers.c"
CLASSES = {"plain": None, "counter": None, "pair": "plain", "viamethod": None, "methodfirst": None, "nativefirst": None,
           "optional": None, "zeroed": None}
STRING_METHOD = {"viamethod", "methodfirst", "nativefirst"}
UNCLASSIFIED_WRITE = """
static zend_object_handlers *choose(void);
static void odd(counter_object *intern)
{
	intern->std.handlers = choose();
}
"""

FAN_OUT = """
static int pick(int key)
{
	switch (key) {
%s
	default: return 99;
	}
}

static int fan(int key)
{
	if (pick(key)) return 7;
	return 7;
}
""" % "\n".join(f"\tcase {n}: return {n + 1};" for n in range(24))


Declaration = collections.namedtuple("Declaration", "classifier parent to_string")


def declaration(parent=None, to_string=False):
    return Declaration("class", parent, to_string)


def declarations():
    return {name: declaration(parent, name in STRING_METHOD) for name, parent in CLASSES.items()}


def fn(name, source=DEMO):
    return Fn(name, Path(source))


class TreeCase(unittest.TestCase):
    """A fixture tree in a temporary directory, with the registration stage run on it once per test."""

    replaced = None

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        fixture_handler_tree.write_tree(self.root, self.replaced)
        self.program = Program(self.root, provenance=True)

    def tearDown(self):
        self.directory.cleanup()


class RegistrationTest(TreeCase):
    def setUp(self):
        super().setUp()
        self.registered = Registered(self.program)

    def slots(self, table, *fields):
        return [self.registered.state.read(f"g:{DEMO}:{table}", (field,)) for field in fields]

    def test_every_registered_class_has_a_region(self):
        self.assertEqual(sorted(CLASSES), self.registered.registered)

    def test_declarator_list_declares_each_table(self):
        tables = self.registered.index.tables
        for name in ("first_handlers", "second_handlers", "counter_handlers", "optional_handlers"):
            self.assertIn(name, tables)
        self.assertEqual(f"g:{DEMO}:second_handlers", tables["second_handlers"][0].region())

    def test_table_copied_from_the_standard_table_takes_its_slots_then_the_slot_writes(self):
        self.assertEqual(
            [fn("counter_cast"), 0, fn("counter_operation")],
            self.slots("counter_handlers", "cast_object", "compare", "do_operation"),
        )

    def test_table_copy_is_a_snapshot_taken_at_the_copy_point(self):
        self.assertEqual(fn("std_compare", STD), self.slots("first_handlers", "compare")[0])
        self.assertEqual(fn("pair_compare"), self.slots("second_handlers", "compare")[0])
        self.assertEqual(fn("pair_cast"), self.slots("second_handlers", "cast_object")[0])

    def test_zeroed_table_holds_only_the_slots_written_after(self):
        self.assertEqual(
            [fn("counter_cast"), 0, 0], self.slots("zeroed_handlers", "cast_object", "compare", "do_operation")
        )

    def test_slot_write_is_relevant_only_in_a_function_that_names_the_table_type(self):
        relevant = self.registered.relevance()
        bodies = {d.name: d.body for d in self.registered.definitions}
        self.assertFalse(relevant(self.definition("unrelated"), bodies["unrelated"]))
        self.assertTrue(relevant(self.definition("zm_startup_demo"), bodies["zm_startup_demo"]))

    def definition(self, name):
        return next(d for d in self.registered.definitions if d.name == name)

    def test_class_entry_takes_the_creator_the_registration_code_wrote(self):
        state = self.registered.state
        self.assertEqual(fn("pair_new"), state.read("c:pair", ("create_object",)))
        self.assertEqual(fn("counter_new"), state.read("c:counter", ("create_object",)))

    def test_class_entry_takes_the_standard_default_table(self):
        pointer = self.registered.state.read("c:plain", ("default_object_handlers",))
        self.assertEqual("g:std_object_handlers", pointer.rid)


class CreationTest(TreeCase):
    def setUp(self):
        super().setUp()
        self.creation = Creation(Registered(self.program))

    def regions(self, name):
        return [table.region for table in self.creation.create(name).tables]

    def test_creator_gives_the_table_it_writes_and_the_struct_it_allocates(self):
        created = self.creation.create("counter")
        self.assertEqual([f"g:{DEMO}:counter_handlers"], [table.region for table in created.tables])
        self.assertEqual("counter_object", created.kind)

    def test_creator_over_the_generic_allocator_overrides_the_default_table(self):
        self.assertEqual([f"g:{DEMO}:second_handlers"], self.regions("pair"))

    def test_class_without_a_creator_takes_the_standard_table(self):
        self.assertEqual(["g:std_object_handlers"], self.regions("plain"))

    def test_table_identity_is_the_source_path_and_symbol(self):
        self.assertEqual([f"{DEMO}:counter_handlers"], [t.identity for t in self.creation.create("counter").tables])

    def test_creations_are_recorded_as_executed_sites(self):
        self.creation.create("counter")
        self.assertTrue(self.creation.executed)


class SitesTest(TreeCase):
    def classify(self):
        registered = Registered(self.program)
        creation = Creation(registered)
        for name in registered.registered:
            creation.create(name)
        return Sites(registered, creation).classify()

    def by_function(self):
        return {d.definition.name: d for d in self.classify()}

    def test_creators_are_creation_sites(self):
        found = self.by_function()
        for name in ("counter_new", "pair_new", "zend_objects_new"):
            self.assertEqual("create", found[name].kind)

    def test_table_taken_from_an_object_of_the_same_struct_is_a_copy(self):
        self.assertEqual(("copy", "counter_object"), self.disposition("copy_counter"))

    def test_named_table_written_to_an_object_is_a_typed_write(self):
        found = self.by_function()["retarget_counter"]
        self.assertEqual(("typed", "counter_object"), (found.kind, found.struct))
        self.assertEqual([f"g:{DEMO}:later_handlers"], [table.region for table in found.tables])

    def test_handlers_member_of_a_struct_that_is_not_an_object_is_foreign(self):
        self.assertEqual(("foreign", None), self.disposition("bind_document"))

    def test_typed_tables_group_by_struct_type(self):
        tables = typed_tables(self.classify())
        self.assertEqual([f"g:{DEMO}:later_handlers"], [t.region for t in tables["counter_object"]])

    def test_unclassified_write_fails_the_extraction(self):
        fixture_handler_tree.write_tree(self.root, {DEMO: fixture_handler_tree.DEMO_C + UNCLASSIFIED_WRITE})
        self.program = Program(self.root, provenance=True)
        with self.assertRaisesRegex(php_src.ExtractionFailure, "odd: unclassified write of a handlers field"):
            self.classify()

    def disposition(self, name):
        found = self.by_function()[name]
        return found.kind, found.struct


class SummaryTest(TreeCase):
    def setUp(self):
        super().setUp()
        self.classes, self.report = read_handler_tables(self.program, declarations())

    def facts(self, name, index=0):
        """The facts of one table alternative: (slot, request) to ('absent') or (symbol, results, dispatch)."""
        found = {}
        for fact in self.classes[name][index].facts:
            key = (fact.slot, fact.request)
            found[key] = "absent" if fact.absent else [
                (t.symbol.split(":")[-1], sorted(t.results), t.dispatch) for t in fact.targets
            ]
        return found

    def test_cast_results_follow_the_type_the_handler_writes(self):
        facts = self.facts("counter")
        self.assertEqual([("counter_cast", ["num"], None)], facts[("cast", "is_long")])
        self.assertEqual([("counter_cast", ["str"], "none")], facts[("cast", "is_string")])
        self.assertEqual([("counter_cast", ["bool"], None)], facts[("cast", "_is_bool")])

    def test_operation_results_follow_the_opcode(self):
        facts = self.facts("counter")
        self.assertEqual([("counter_operation", ["num"], None)], facts[("operation", "zend_add")])
        self.assertEqual([("counter_operation", ["bool"], None)], facts[("operation", "zend_sub")])

    def test_only_the_requests_the_engine_makes_are_summarized(self):
        requests = {request for slot, request in self.facts("counter") if slot == "operation"}
        self.assertEqual({"zend_add", "zend_sub"}, requests)

    def test_null_slot_is_a_whole_slot_absence(self):
        self.assertEqual("absent", self.facts("counter")[("compare", None)])
        self.assertEqual("absent", self.facts("pair")[("operation", None)])

    def test_compare_that_can_return_normally_yields_the_number_kind(self):
        self.assertEqual([("pair_compare", ["num"], None)], self.facts("pair")[("compare", None)])

    def test_cast_that_always_throws_has_a_present_fact_with_no_result(self):
        self.assertEqual([("pair_cast", [], None)], self.facts("pair")[("cast", "is_long")])

    def test_class_without_a_creator_reads_the_standard_table(self):
        self.assertEqual(f"{STD}:std_object_handlers", self.classes["plain"][0].identifier)
        self.assertEqual([("std_cast", ["str"], "none")], self.facts("plain")[("cast", "is_string")])

    def test_string_conversion_through_the_method_alone(self):
        self.assertEqual([("via_cast", ["any"], "method_only")], self.facts("viamethod")[("cast", "is_string")])

    def test_method_called_before_the_native_write_is_method_first(self):
        self.assertEqual([("method_first_cast", ["str"], "method_first")], self.facts("methodfirst")[("cast", "is_string")])

    def test_native_write_before_the_method_call_is_native_first(self):
        self.assertEqual([("native_first_cast", ["any"], "native_first")], self.facts("nativefirst")[("cast", "is_string")])

    def test_typed_write_adds_a_table_to_every_class_of_the_struct(self):
        self.assertEqual(
            [f"{DEMO}:counter_handlers", f"{DEMO}:later_handlers"], [t.identifier for t in self.classes["counter"]]
        )

    def test_conditional_slot_gives_one_table_alternative_per_configuration(self):
        found = {t.identifier: t for t in self.classes["optional"]}
        self.assertEqual(
            {f"{DEMO}:optional_handlers #defined(FEATURE_COMPARE)", f"{DEMO}:optional_handlers #!defined(FEATURE_COMPARE)"},
            set(found),
        )
        compare = {i: [t.symbol.split(":")[-1] for f in tb.facts if f.slot == "compare" for t in f.targets]
                   for i, tb in found.items()}
        self.assertEqual(["pair_compare"], compare[f"{DEMO}:optional_handlers #defined(FEATURE_COMPARE)"])
        self.assertEqual(["std_compare"], compare[f"{DEMO}:optional_handlers #!defined(FEATURE_COMPARE)"])

    def test_every_summary_was_established(self):
        self.assertEqual([], self.report.omitted)

    def test_class_without_a_declaration_gets_no_tables(self):
        classes, _ = read_handler_tables(self.program, {"plain": declarations()["plain"]})
        self.assertEqual(["plain"], list(classes))

    def test_effective_string_method_follows_the_parent_chain(self):
        found = {
            "child": declaration("base"),
            "base": declaration(to_string=True),
        }
        self.assertTrue(effective_string_method(found, "child"))
        self.assertFalse(effective_string_method({**found, "base": declaration()}, "child"))


class MachineTest(TreeCase):
    replaced = {DEMO: fixture_handler_tree.DEMO_C + FAN_OUT}

    def exits(self, name):
        registered = Registered(self.program)
        machine = registered.machine
        machine.policy = SummaryPolicy()
        definition = self.program.functions[name][0]
        return machine.call(definition, [Ptr("o:key", ())], registered.state.fork(), 100000)

    def test_states_returning_together_leave_as_one_exit(self):
        exits, complete = self.exits("fan")
        self.assertTrue(complete)
        self.assertEqual([7], [value for value, _ in exits])

    def test_exits_that_differ_in_their_result_stay_apart(self):
        exits, complete = self.exits("pick")
        self.assertTrue(complete)
        self.assertEqual(25, len(exits))


class RenderTest(unittest.TestCase):
    def test_no_table_renders_nothing(self):
        self.assertEqual("", render_handlers([]))

    def test_unresolved_table_renders_an_empty_fact_list(self):
        self.assertEqual("    handlers:\n      - id: a.c:t\n        facts: []\n", render_handlers([Table("a.c:t")]))

    def test_identifier_with_a_branch_suffix_is_quoted(self):
        text = render_handlers([Table("a.c:t #defined(X)")])
        self.assertIn('- id: "a.c:t #defined(X)"', text)


if __name__ == "__main__":
    unittest.main()
