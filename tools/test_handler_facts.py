"""Tests for the handler extraction (design-extraction-handlers.md, spec-extraction-handlers.md) over the small tree of
fixture_handler_tree.py.

Run: python3 -B -m unittest discover -s tools -p "test_*.py" (from the externs-phpstubs root).
- registration: classes registered, tables indexed from a declarator list, a table copied before a later slot write,
  slot writes read only in functions that name the table type, the parent's creator and table inherited
- creation: the creator's table of each class, the struct type it allocates, the default table of a class with no creator
- write sites: creation, copy, typed and foreign dispositions; a write that fits none fails the extraction
- test_finite_recursive_helper_has_num_result: four terminating calls establish NUM
- test_hundred_recursive_inputs_keep_num: a terminating 100-call helper needs no Python recursion
- test_suspended_ancestor_slice_keeps_later_root_write: a nested slice resumes its owning caller
- test_suspended_instruction_keeps_inline_locals: dependency admission preserves an instruction checkpoint
- test_mutual_recursion_has_num_result: mutually recursive procedures reach the base write
- test_recursive_local_output_alias_has_num_result: recursive argument aliases retain their effects
- test_recursive_call_keeps_caller_locals: callee effects cannot overwrite private caller locals
- test_recursive_fixed_input_keeps_only_normal_results: a recursive component joins terminating exits
- test_step_budget_exhaustion_is_unestablished: exhausting total work never establishes a result
- test_pending_budget_exhaustion_is_unestablished: exhausting queued states never establishes a result
- test_exit_fold_keeps_every_normal_kind: folding 80 normal exits retains NUM and STR
- test_aggregate_alternatives_keep_every_result_kind: a by-value conditional struct copy keeps NUM and STR
- test_compare_closes_num_bound_after_a_normal_exit: remaining C return values cannot add a non-NUM kind
- test_inline_expression_is_not_a_normal_compare_exit: an expression value cannot close a throwing request
- test_unread_callee_invalidates_a_canonical_local: a procedure input keeps unknown pointer writes
- test_completed_callees_keep_the_request_budget: settled direct calls are reused during component iteration
- test_scalar_argument_retains_its_member_alias: argument renaming preserves equality with a member read
- test_declared_noreturn_call_has_no_normal_result: a declared C non-returning call cannot reach SUCCESS
- test_procedure_size_values_reach_fixpoint: sizeof values compare by source type rather than allocation identity
- test_recursive_component_without_exit_has_no_normal_result: a stable empty component has no normal exit
- test_cached_effects_rebind_argument_regions: the same helper writes each caller argument
- test_unknown_type_is_unestablished: an unread type helper cannot establish ANY
- test_unwritten_success_is_unestablished: SUCCESS without an output write has no proved result
- test_expression_bound_keeps_every_alternative: every one of 49 value alternatives is visited
- test_source_alternative_bound_keeps_str: the last source branch contributes STR
- test_conditional_callee_definitions_keep_str: all matching helper definitions contribute
- test_conditional_definitions_keep_both_results: every conditional definition contributes normal results
- request summaries: result kinds per cast and operation request, a compare that may return, string dispatch order,
  conditional slots as two table alternatives, absent slots, the rendered handlers field
- the handler write patterns of php-src (testdata/handlers): repeated and aliased writes, direct and snapshot copies,
  aggregate tables, helper arguments, class-fixed creators, inherited creators, typed lifetime writes, final writes
  after conversion, pending exceptions, COM's guard, and finite recursive procedure summaries
"""

import collections
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import extract_hierarchy
import handler_machine
import handler_summary
import fixture_handler_tree
import php_src
from handler_create import Creation
from handler_facts import effective_string_method, read_handler_tables
from handler_expr import Expressions
from handler_memory import Alt, Fn, Ptr, alternatives
from handler_machine import EXIT_BATCH
from handler_minit import Registered
from handler_render import Table, render_handlers
from handler_sites import Sites, typed_tables
from handler_summary import Summarizer, SummaryPolicy
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

static int through(int key)
{
	return fan(key) + 1;
}

static int fan(int key)
{
	switch (key) {
%s
	default: return 7;
	}
}
""" % ("\n".join(f"\tcase {n}: return {n + 1};" for n in range(24)), "\n".join(f"\tcase {n}: return 7;" for n in range(120)))


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

    def test_exits_of_one_history_are_joined_when_they_pile_up(self):
        exits, complete = self.exits("fan")
        self.assertTrue(complete)
        self.assertLessEqual(len(exits), EXIT_BATCH)
        self.assertEqual({7}, {value for value, _ in exits})

    def test_a_caller_of_many_exits_keeps_every_outcome_as_one(self):
        exits, complete = self.exits("through")
        self.assertTrue(complete)
        self.assertEqual({8}, {value for value, _ in exits})

    def test_exits_that_differ_in_their_result_stay_apart(self):
        exits, complete = self.exits("pick")
        self.assertTrue(complete)
        self.assertEqual(25, len(exits))

    def test_outcomes_of_equal_states_become_one_outcome_of_alternatives(self):
        state = Registered(self.program).state
        first, second = state.fork(), state.fork()
        merged = Expressions.merged([(1, first), (2, second), (1, state.fork())])
        self.assertEqual(1, len(merged))
        self.assertEqual({(1, ()), (2, ())}, set(alternatives(merged[0][0])))

    def test_outcomes_of_different_states_stay_apart(self):
        state = Registered(self.program).state
        written, tagged = state.fork(), state.fork()
        written.write("g:x", (), 5)
        tagged.tags = frozenset({"defined(X)"})
        merged = Expressions.merged([(1, state.fork()), (1, written), (1, tagged)])
        self.assertEqual(3, len(merged))


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


def moves(fact):
    """The comparable form of a fact: ``absent`` or the (target function, result kinds, string dispatch) triples."""
    if fact.absent:
        return "absent"
    return [(t.symbol.split(":")[-1], sorted(t.results), t.dispatch) for t in fact.targets]


class RealShapeTest(unittest.TestCase):
    """The extraction over the handler write patterns of php-src in their smallest form (testdata/handlers)."""

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        fixture_handler_tree.write_real_tree(root)
        cls.declarations = extract_hierarchy.read_php_src(root)
        cls.classes, cls.report = read_handler_tables(Program(root, provenance=True), cls.declarations)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def tables(self, name):
        """The table alternatives of a class by identifier, each as {(slot, request): moves}."""
        return {t.identifier.split(":")[-1]: {(f.slot, f.request): moves(f) for f in t.facts}
                for t in self.classes[name]}

    def cast(self, name, table, request="is_long"):
        return self.tables(name)[table][("cast", request)]

    def test_every_source_pattern_is_established(self):
        self.assertEqual([], self.report.omitted)

    def test_finite_helper_result_is_established_for_each_request(self):
        facts = self.tables("rrec")["rec_handlers"]
        for request in ("is_long", "is_string", "_is_bool"):
            dispatch = "none" if request == "is_string" else None
            self.assertEqual([("rec_cast", ["num"], dispatch)], facts[("cast", request)])
        self.assertEqual([("std_compare", ["num"], None)], facts[("compare", None)])

    def test_repeated_assignment_of_the_same_slot_keeps_the_last_write_of_that_table(self):
        self.assertEqual([("cast_sdl", ["bool"], None)], self.cast("rurl", "url_handlers"))
        self.assertEqual([("std_cast", [], None)], self.cast("rsdl", "sdl_handlers"))

    def test_direct_struct_copy_takes_the_standard_slots_then_the_later_writes(self):
        facts = self.tables("rbundle")["bundle_handlers"]
        self.assertEqual([("std_cast", [], None)], facts[("cast", "is_long")])
        self.assertEqual([("compare_unordered", ["num"], None)], facts[("compare", None)])

    def test_aggregate_tables_by_position_by_designator_and_zeroed(self):
        self.assertEqual([("cast_long", ["num"], None)], self.cast("rpos", "positional_handlers"))
        self.assertEqual([("compare_throwing", [], None)], self.tables("rpos")["positional_handlers"][("compare", None)])
        self.assertEqual([("cast_string", ["str"], None)], self.cast("rdes", "designated_handlers"))
        zeroed = self.tables("rzero")["zero_handlers"]
        self.assertEqual("absent", zeroed[("compare", None)])
        self.assertEqual([("cast_long", ["num"], None)], zeroed[("cast", "is_long")])

    def test_copy_is_a_snapshot_and_a_child_without_a_creator_takes_the_parent_table(self):
        self.assertEqual([("std_cast", [], None)], self.cast("rsnap", "snap_handlers"))
        self.assertEqual([("cast_string", ["str"], None)], self.cast("rbase", "base_handlers"))
        self.assertEqual(self.tables("rbase")["base_handlers"], self.tables("rchild")["base_handlers"])

    def test_pointer_alias_taken_after_the_initialization_writes_the_aliased_table(self):
        self.assertEqual([("cast_long", ["num"], None)], self.cast("ralias", "alias_handlers"))

    def test_conditional_compilation_gives_one_table_alternative_per_configuration(self):
        casts = sorted(str(table[("cast", None)] if ("cast", None) in table else table[("cast", "is_long")])
                       for table in self.tables("rcond").values())
        self.assertEqual(2, len(self.classes["rcond"]))
        self.assertEqual(sorted(["absent", str([("cast_long", ["num"], None)])]), casts)

    def test_creator_helper_takes_its_table_from_each_class_creator(self):
        self.assertEqual([("cast_long", ["num"], None)], self.cast("rtidya", "tidy_doc_handlers"))
        self.assertEqual([("cast_string", ["str"], None)], self.cast("rtidyb", "tidy_node_handlers"))

    def test_class_fixed_creator_picks_the_table_by_the_class_and_its_ancestors(self):
        self.assertEqual([("cast_long", ["num"], None)], self.cast("rlink", "link_handlers"))
        self.assertEqual([("cast_string", ["str"], None)], self.cast("rstmt", "stmt_handlers"))
        self.assertEqual([("std_cast", [], None)], self.cast("rother", "plain_link_handlers"))

    def test_registered_subclass_of_a_class_fixed_creator_takes_the_parent_table(self):
        self.assertEqual(self.tables("rlink"), self.tables("rlinkchild"))

    def test_class_fixed_creator_gives_no_other_class_the_tables_it_does_not_pick(self):
        for name in ("rother", "rstmt", "rtidya", "rtidyb"):
            self.assertEqual(1, len(self.classes[name]), name)
        self.assertEqual({"plain_link_handlers"}, set(self.tables("rother")))

    def test_object_result_is_any_and_a_number_branch_adds_num(self):
        self.assertEqual([("gmp_operation", ["any"], None)], self.tables("rgmp")["gmp_handlers"][("operation", "zend_add")])
        self.assertEqual([("gmp_operation", ["any"], None)], self.tables("rgmp")["gmp_handlers"][("operation", "zend_sub")])
        ordinary = self.tables("rcdata")["cdata_handlers"]
        self.assertEqual([("cdata_operation", ["any"], None)], ordinary[("operation", "zend_add")])
        self.assertEqual([("cdata_operation", ["any", "num"], None)], ordinary[("operation", "zend_sub")])

    def test_lifetime_writes_give_the_ordinary_value_and_freed_tables(self):
        found = self.tables("rcdata")
        self.assertEqual(["cdata_handlers", "cdata_value_handlers", "cdata_free_handlers"], list(found))
        self.assertEqual("absent", found["cdata_value_handlers"][("operation", None)])
        self.assertEqual([("cdata_free_cast", [], None)], found["cdata_free_handlers"][("cast", "is_long")])
        self.assertEqual("absent", found["cdata_free_handlers"][("compare", None)])

    def test_typed_write_reaches_only_the_classes_of_its_struct_and_a_pointer_copy_writes_none(self):
        dispositions = {(d.kind, d.definition.name) for d in self.report.dispositions}
        self.assertIn(("typed", "cdata_into_value"), dispositions)
        self.assertNotIn("cdata_pointer_free", {name for _, name in dispositions})
        self.assertEqual(1, len(self.classes["rgmp"]))

    def test_normal_final_write_after_conversion_decides_the_kind(self):
        found = self.tables("rconv")["conv_handlers"]
        self.assertEqual([("conv_cast", ["num"], None)], found[("cast", "is_long")])
        self.assertEqual([("conv_cast", ["str"], "none")], found[("cast", "is_string")])
        self.assertEqual([("conv_cast", ["bool"], None)], found[("cast", "_is_bool")])

    def test_pending_exception_is_no_normal_result_whatever_the_function_returns(self):
        found = self.tables("rexc")["exc_handlers"]
        self.assertEqual([("exc_cast", [], None)], found[("cast", "is_long")])
        self.assertEqual([("exc_cast", ["num"], "none")], found[("cast", "is_string")])

    def test_nonthrowing_compare_sentinel_yields_num_and_a_throwing_one_none(self):
        self.assertEqual([("compare_unordered", ["num"], None)], self.tables("rdes")["designated_handlers"][("compare", None)])
        self.assertEqual([("compare_throwing", [], None)], self.tables("rpos")["positional_handlers"][("compare", None)])

    def test_com_cast_is_any_through_the_variant_guard_and_native_first_on_failure(self):
        found = self.tables("rcom")["com_handlers"]
        self.assertEqual([("com_cast", ["any", "num", "str"], None)], found[("cast", "is_long")])
        self.assertEqual([("com_cast", ["any", "num", "str"], "native_first")], found[("cast", "is_string")])
        self.assertEqual([("com_cast", ["any", "num", "str"], None)], found[("cast", "_is_bool")])

    def test_registered_interface_and_enum_have_no_tables_and_no_registered_flag(self):
        self.assertNotIn("rface", self.classes)
        self.assertNotIn("renum", self.classes)
        self.assertEqual("interface", self.declarations["rface"].classifier)
        self.assertEqual("enum", self.declarations["renum"].classifier)


class SummaryCoverageTest(TreeCase):
    def summary(self, code):
        start = fixture_handler_tree.DEMO_C.index("static int counter_cast(")
        end = fixture_handler_tree.DEMO_C.index("static int counter_operation(")
        fixture_handler_tree.write_tree(self.root, {
            DEMO: fixture_handler_tree.DEMO_C[:start] + code + fixture_handler_tree.DEMO_C[end:]
        })
        registered = Registered(Program(self.root, provenance=True))
        return Summarizer(registered).cast(fn("counter_cast"), "IS_LONG", False)

    def test_conditional_definitions_keep_both_results(self):
        summary = self.summary("""
#ifdef FEATURE_COMPARE
static int counter_cast(zend_object *o,zval *out,int type) { ZVAL_LONG(out,1);return SUCCESS; }
#else
static int counter_cast(zend_object *o,zval *out,int type) { ZVAL_STR(out,NULL);return SUCCESS; }
#endif
""")
        self.assertEqual(frozenset({"num", "str"}), summary.results)

    def test_expression_bound_keeps_every_alternative(self):
        value = Alt(tuple((n, ()) for n in range(49)))
        machine = Expressions()
        state = Registered(self.program).state
        self.assertEqual(set(range(49)), {v for v, _ in machine.alts(value, state)})

    def test_source_alternative_bound_keeps_str(self):
        functions = "\n".join(
            f"static int f{n}(zend_object *o,zval *out,int t) {{ZVAL_LONG(out,1);return SUCCESS;}}"
            for n in range(48)
        )
        functions += "\nstatic int f48(zend_object *o,zval *out,int t) {ZVAL_STR(out,NULL);return SUCCESS;}\n"
        branches = "\n".join(
            ("#if" if n == 0 else "#elif") + f" defined(CHOICE_{n})\n.selected=f{n}," for n in range(48)
        )
        code = functions + "struct dispatch {int (*selected)(zend_object *o,zval *out,int t);};\n"
        code += "static int counter_cast(zend_object *o,zval *out,int t) {struct dispatch d={\n" + branches
        code += "\n#else\n.selected=f48,\n#endif\n};return d.selected(o,out,t);}"
        self.assertEqual(frozenset({"num", "str"}), self.summary(code).results)

    def test_conditional_callee_definitions_keep_str(self):
        branches = "\n".join(
            ("#if" if n == 0 else "#elif") + f" defined(CHOICE_{n})\n"
            "static int fill(zval *out) {ZVAL_LONG(out,1);return SUCCESS;}" for n in range(48)
        )
        code = branches + "\n#else\nstatic int fill(zval *out) {ZVAL_STR(out,NULL);return SUCCESS;}\n#endif\n"
        code += "static int counter_cast(zend_object *o,zval *out,int t) {return fill(out);}"
        self.assertEqual(frozenset({"num", "str"}), self.summary(code).results)

    def test_unknown_type_is_unestablished(self):
        summary = self.summary(
            "static int counter_cast(zend_object *o,zval *out,int type) "
            "{ Z_TYPE_INFO_P(out)=unknown_type();return SUCCESS; }"
        )
        self.assertIsNone(summary.results)

    def test_unwritten_success_is_unestablished(self):
        summary = self.summary("static int counter_cast(zend_object *o,zval *out,int type) {return SUCCESS;}")
        self.assertIsNone(summary.results)

    def test_finite_recursive_helper_has_num_result(self):
        fixture_handler_tree.write_real_tree(self.root)
        registered = Registered(Program(self.root, provenance=True))
        summary = Summarizer(registered).cast(fn("rec_cast", "ext/real/real.c"), "IS_LONG", False)
        self.assertEqual(frozenset({"num"}), summary.results)

    def test_mutual_recursion_has_num_result(self):
        summary = self.summary("""
static void left(zval *out,int n) {if(n) right(out,n-1);else ZVAL_LONG(out,1);}
static void right(zval *out,int n) {if(n) left(out,n-1);else ZVAL_LONG(out,1);}
static int counter_cast(zend_object *o,zval *out,int t) {left(out,7);return SUCCESS;}
""")
        self.assertEqual(frozenset({"num"}), summary.results)

    def test_recursive_local_output_alias_has_num_result(self):
        summary = self.summary("""
static void fill(zval *out,int n) {
    if(n) {zval tmp;fill(&tmp,n-1);Z_TYPE_INFO_P(out)=Z_TYPE_INFO_P(&tmp);}
    else {ZVAL_LONG(out,1);}
}
static int counter_cast(zend_object *o,zval *out,int t) {fill(out,4);return SUCCESS;}
""")
        self.assertEqual(frozenset({"num"}), summary.results)

    def test_recursive_call_keeps_caller_locals(self):
        summary = self.summary("""
static void fill(zval *out,int n) {
    if(n) {int kept=n;fill(out,n-1);if(kept != n) ZVAL_STR(out,NULL);}
    else {ZVAL_LONG(out,1);}
}
static int counter_cast(zend_object *o,zval *out,int t) {fill(out,4);return SUCCESS;}
""")
        self.assertEqual(frozenset({"num"}), summary.results)

    def test_recursive_fixed_input_keeps_only_normal_results(self):
        summary = self.summary("""
static void fill(zval *out,zend_object *o) {
    if(o->some_native_flag) {fill(out,o);} else {ZVAL_LONG(out,1);}
}
static int counter_cast(zend_object *o,zval *out,int t) {fill(out,o);return SUCCESS;}
""")
        self.assertEqual(frozenset({"num"}), summary.results)

    def test_cached_effects_rebind_argument_regions(self):
        summary = self.summary("""
static void fill(zval *out) {ZVAL_LONG(out,1);}
static int counter_cast(zend_object *o,zval *out,int t) {
    zval first;zval second;fill(&first);fill(&second);
    Z_TYPE_INFO_P(out)=Z_TYPE_INFO_P(&first);
    if(Z_TYPE_INFO_P(&second) != IS_LONG) ZVAL_STR(out,NULL);
    return SUCCESS;
}
""")
        self.assertEqual(frozenset({"num"}), summary.results)

    def test_step_budget_exhaustion_is_unestablished(self):
        old = handler_summary.SUMMARY_BUDGET
        try:
            handler_summary.SUMMARY_BUDGET = 0
            summary = self.summary(
                "static int counter_cast(zend_object *o,zval *out,int type) {ZVAL_LONG(out,1);return SUCCESS;}"
            )
            self.assertIsNone(summary.results)
        finally:
            handler_summary.SUMMARY_BUDGET = old

    def test_pending_budget_exhaustion_is_unestablished(self):
        registered = Registered(self.program)
        old = handler_machine.PENDING_CAP
        try:
            handler_machine.PENDING_CAP = 0
            summary = Summarizer(registered).cast(fn("counter_cast"), "IS_LONG", False)
            self.assertIsNone(summary.results)
        finally:
            handler_machine.PENDING_CAP = old

    def test_exit_fold_keeps_every_normal_kind(self):
        cases = "\n".join(f"case {n}: ZVAL_LONG(out,{n}); return SUCCESS;" for n in range(80))
        summary = self.summary(
            "static int counter_cast(zend_object *o,zval *out,int type) {switch(o->some_native_flag) {"
            + cases + "default: ZVAL_STR(out,NULL);return SUCCESS;}}"
        )
        self.assertEqual(frozenset({"num", "str"}), summary.results)

    def test_recursive_component_without_exit_has_no_normal_result(self):
        summary = self.summary("""
static void fill(zval *out) {fill(out);}
static int counter_cast(zend_object *o,zval *out,int t) {fill(out);return SUCCESS;}
""")
        self.assertEqual(frozenset(), summary.results)

    def test_procedure_size_values_reach_fixpoint(self):
        old = handler_summary.SUMMARY_BUDGET
        try:
            handler_summary.SUMMARY_BUDGET = 200
            summary = self.summary("""
static size_t amount(void) {return sizeof(int);}
static int counter_cast(zend_object *o,zval *out,int t) {amount();ZVAL_LONG(out,1);return SUCCESS;}
""")
            self.assertEqual(frozenset({"num"}), summary.results)
        finally:
            handler_summary.SUMMARY_BUDGET = old

    def test_declared_noreturn_call_has_no_normal_result(self):
        summary = self.summary("""
extern void work(zval *out);
static ZEND_NORETURN void halt(zval *out) {for(;;) {work(out);}}
static int counter_cast(zend_object *o,zval *out,int t) {halt(out);return SUCCESS;}
""")
        self.assertEqual(frozenset(), summary.results)

    def test_scalar_argument_retains_its_member_alias(self):
        summary = self.summary("""
static int same(zend_object *o,zval *out,int flag) {
    if(flag != o->some_flag) {ZVAL_STR(out,NULL);} else {ZVAL_LONG(out,1);}
    return SUCCESS;
}
static int counter_cast(zend_object *o,zval *out,int t) {return same(o,out,o->some_flag);}
""")
        self.assertEqual(frozenset({"num"}), summary.results)

    def test_compare_closes_num_bound_after_a_normal_exit(self):
        code = fixture_handler_tree.DEMO_C + """
extern void work(zval *out);
static int unfinished(zval *a,zval *b) {""" + "work(a);" * 100 + """return 0;}
static int projected_compare(zval *a,zval *b) {
    if(Z_TYPE_P(a) == IS_LONG) return 0;
    return unfinished(a,b);
}
"""
        fixture_handler_tree.write_tree(self.root, {DEMO: code})
        registered = Registered(Program(self.root, provenance=True))
        old = handler_summary.SUMMARY_BUDGET
        try:
            handler_summary.SUMMARY_BUDGET = 20
            summary = Summarizer(registered).compare(fn("projected_compare"))
            self.assertEqual(frozenset({"num"}), summary.results)
        finally:
            handler_summary.SUMMARY_BUDGET = old

    def test_inline_expression_is_not_a_normal_compare_exit(self):
        code = fixture_handler_tree.DEMO_C + """
static int inline_compare(zval *a,zval *b) {
    int value=({int x=1;x;});
    zend_throw_error(NULL,"no normal exit");return value;
}
"""
        fixture_handler_tree.write_tree(self.root, {DEMO: code})
        registered = Registered(Program(self.root, provenance=True))
        self.assertEqual(frozenset(), Summarizer(registered).compare(fn("inline_compare")).results)

    def test_aggregate_alternatives_keep_every_result_kind(self):
        summary = self.summary("""
static int counter_cast(zend_object *o,zval *out,int t) {
    zval first;ZVAL_LONG(&first,1);
    zval second;ZVAL_STR(&second,NULL);
    zval chosen=unknown_flag() ? first : second;
    Z_TYPE_INFO_P(out)=Z_TYPE_INFO(chosen);
    return SUCCESS;
}
""")
        self.assertEqual(frozenset({"num", "str"}), summary.results)

    def test_unread_callee_invalidates_a_canonical_local(self):
        summary = self.summary("""
extern void opaque(zval *out);
static void fill(zval *out) {opaque(out);}
static int counter_cast(zend_object *o,zval *out,int t) {
    zval local;ZVAL_LONG(&local,1);fill(&local);
    Z_TYPE_INFO_P(out)=Z_TYPE_INFO(local);return SUCCESS;
}
""")
        self.assertIsNone(summary.results)

    def test_completed_callees_keep_the_request_budget(self):
        old = handler_summary.SUMMARY_BUDGET
        try:
            handler_summary.SUMMARY_BUDGET = 100
            summary = self.summary("""
static size_t amount(int n) {return sizeof(int);}
static int counter_cast(zend_object *o,zval *out,int t) {""" + "".join(
                f"amount({i});" for i in range(20)) + """ZVAL_LONG(out,1);return SUCCESS;}
""")
            self.assertEqual(frozenset({"num"}), summary.results)
        finally:
            handler_summary.SUMMARY_BUDGET = old


    def test_hundred_recursive_inputs_keep_num(self):
        summary = self.summary("""
static void fill(zval *out,int n) {
    if(n) fill(out,n-1); else ZVAL_LONG(out,1);
}
static int counter_cast(zend_object *o,zval *out,int t) {
    fill(out,100); return SUCCESS;
}
""")
        self.assertEqual(frozenset({"num"}), summary.results)

    def test_suspended_instruction_keeps_inline_locals(self):
        summary = self.summary("""
static int amount(int n) {return n;}
static int counter_cast(zend_object *o,zval *out,int t) {
    int n=1;
    int value=({int local=n++;local+amount(n++);});
    if(n==3 && value==3) ZVAL_LONG(out,1); else ZVAL_STR(out,NULL);
    return SUCCESS;
}
""")
        self.assertEqual(frozenset({"num"}), summary.results)


    def test_suspended_ancestor_slice_keeps_later_root_write(self):
        previous = handler_summary.CALL_SLICE
        try:
            handler_summary.CALL_SLICE = 5
            summary = self.summary("""
static void inner(zval *out) {""" + "unknown_flag();" * 12 + """}
static void outer(zval *out) {inner(out);ZVAL_LONG(out,1);}
static int counter_cast(zend_object *o,zval *out,int t) {
    outer(out);ZVAL_STR(out,NULL);return SUCCESS;
}
""")
            self.assertEqual(frozenset({"str"}), summary.results)
        finally:
            handler_summary.CALL_SLICE = previous
