package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.GuardValue
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.Propagation
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.SubjectModel
import edu.jhu.cobra.commons.phpmodels.ValueSemantics
import edu.jhu.cobra.commons.phpmodels.Verification
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for the hand-maintained value rules set rooted at [StubResources.VALUE_RULES].
 *
 * - `value rules set loads without a vocabulary` — verifies the set names no category or color
 * - `value rules set is manually verified` — verifies the set's provenance
 * - `every value rules entry is an unsigned model asserting only the value unit` — verifies the shape rule
 * - `every value rules subject is a registry declaration` — verifies existence in the generated declarations
 * - `no value rules unit repeats the generated unit` — verifies each default-branch unit differs from the registry's
 * - `mode-switching subjects carry a guarded branch and a default branch` — verifies print_r and var_export
 * - `representative units follow the PHP manual` — verifies typed results and flow sets
 */
internal class ValueRulesSetTest {
    private val rules by lazy { DocumentSetLoader.load(StubResources.opener(StubResources.VALUE_RULES)) }

    private val registry by lazy { StubLoader.loadAll() }

    private val models: List<SubjectModel> by lazy { rules.entries.map { it as SubjectModel } }

    private val defaults: Map<ModelSubject, SubjectModel> by lazy { models.filter { it.guard == null }.associateBy { it.subject } }

    @Test
    fun `value rules set loads without a vocabulary`() {
        assertTrue(rules.entries.isNotEmpty())
        assertTrue(rules.vocabulary.vulnClasses.isEmpty())
        assertTrue(rules.vocabulary.provenances.isEmpty())
        assertTrue(rules.policy.isEmpty())
    }

    @Test
    fun `value rules set is manually verified`() {
        assertEquals(Verification.MANUAL, assertNotNull(rules.provenance).verification)
    }

    @Test
    fun `every value rules entry is an unsigned model asserting only the value unit`() {
        for (model in models) {
            assertNull(model.signature, "${model.subject}")
            assertNotNull(model.body.returns, "${model.subject}")
            assertNull(model.body.sources, "${model.subject}")
            assertNull(model.body.sinks, "${model.subject}")
            assertNull(model.body.sanitizers, "${model.subject}")
        }
    }

    @Test
    fun `every value rules subject is a registry declaration`() {
        val declared = registry.functions.keys + registry.methods.keys
        val missing = models.map { it.subject }.filter { it !in declared }
        assertTrue(missing.isEmpty(), "Subjects absent from the registry: $missing")
    }

    @Test
    fun `no value rules unit repeats the generated unit`() {
        for ((subject, model) in defaults) {
            val generated = (registry.functions[subject] ?: registry.methods[subject])!!.model.body.valueSemantics()
            assertNotEquals(generated, model.body.valueSemantics(), "$subject")
        }
    }

    @Test
    fun `mode-switching subjects carry a guarded branch and a default branch`() {
        for (name in listOf("print_r", "var_export")) {
            val branches = models.filter { it.subject == FunctionSubject(name) }
            assertEquals(2, branches.size, name)
            val guarded = branches.single { it.guard != null }
            assertEquals(Port.Argument(1), guarded.guard!!.port)
            assertEquals(GuardValue.BoolValue(true), guarded.guard!!.value)
            assertEquals(ValueSemantics(ReturnKind.STR, listOf(argumentToReturn(0))), guarded.body.valueSemantics())
            assertTrue(branches.single { it.guard == null }.body.propagation == null, name)
        }
    }

    @Test
    fun `representative units follow the PHP manual`() {
        assertEquals(ValueSemantics(ReturnKind.NUM, listOf(argumentToReturn(0))), unitOf("strlen"))
        assertEquals(ValueSemantics(ReturnKind.STR, emptyList()), unitOf("getenv"))
        assertEquals(ValueSemantics(ReturnKind.STR, listOf(argumentToReturn(0))), unitOf("strstr"))
        assertEquals(ValueSemantics(ReturnKind.NUM, emptyList()), unitOf("print"))
        assertEquals(
            ValueSemantics(ReturnKind.ANY, listOf(Propagation(from = Port.Argument(0), to = Port.Argument(1)))),
            unitOf("parse_str"),
        )
        assertNull(defaults[FunctionSubject("crypt")])
        assertNull(defaults[FunctionSubject("str_increment")])
    }

    private fun unitOf(name: String): ValueSemantics = defaults.getValue(FunctionSubject(name)).body.valueSemantics()!!

    private fun argumentToReturn(position: Int): Propagation = Propagation(from = Port.Argument(position), to = Port.Return)
}
