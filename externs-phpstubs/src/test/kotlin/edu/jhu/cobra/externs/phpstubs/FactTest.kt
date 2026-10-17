package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ArgPattern
import edu.jhu.cobra.commons.phpmodels.ArgumentCheck
import edu.jhu.cobra.commons.phpmodels.CharacterBound
import edu.jhu.cobra.commons.phpmodels.CharacterClass
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.SourceKindId
import edu.jhu.cobra.commons.phpmodels.Verification
import edu.jhu.cobra.commons.phpmodels.VulnTypeId
import edu.jhu.cobra.commons.value.BoolVal
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

/**
 * Tests for the [Fact] kinds a merged record exposes: each carries its owner and the condition of its entry.
 *
 * - `an unconditional entry yields facts without a condition` — verifies the null condition
 * - `a conditional entry tags every fact with its pattern` — verifies condition propagation per fact kind
 * - `a sanitizer fact keeps its check` — verifies the checked argument, accepting value, and class
 * - `a source fact keeps its site and key patterns` — verifies the by-reference source shape
 * - `a source fact at the result has no site` — verifies the result-site source shape
 * - `a returns fact and its flow facts come from one value unit` — verifies the classification and the ports
 * - `a characters fact comes from the value unit` — verifies the bound is read with returns and flows
 * - `a throws fact holds the whole class set` — verifies one fact per throws unit
 * - `an empty throws section is a fact` — verifies the assertion that a call throws none
 */
internal class FactTest {
    private val f = FunctionSubject("f")

    @Test
    fun `an unconditional entry yields facts without a condition`() {
        val document = "- subject: {function: f}\n  sinks: [{port: argument(1), vulnType: xss}]\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        assertEquals(SinkFact(f, null, Port.Argument(1), VulnTypeId("xss")), record.sinkFacts.single())
    }

    @Test
    fun `a conditional entry tags every fact with its pattern`() {
        val document =
            """
            - subject: {function: f}
              when: [true]
              sanitizers: [{vulnTypes: [sqli]}]
              returns: str
              propagation: [{from: argument(0), to: return}]
            """.trimIndent()
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        val condition = ArgPattern(listOf(BoolVal(true)))
        assertEquals(SanitizerFact(f, condition, setOf(VulnTypeId("sqli")), null), record.sanitizerFacts.single())
        assertEquals(condition, record.returns.single().condition)
        assertEquals(FlowFact(f, condition, Port.Argument(0), Port.Return), record.flows.single())
    }

    @Test
    fun `a sanitizer fact keeps its check`() {
        val document =
            "- subject: {function: f}\n  sanitizers: [{check: {argument: argument(0), accepts: true, within: '[0-9]'}}]\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        val check = ArgumentCheck(Port.Argument(0), BoolVal(true), CharacterClass("[0-9]"))
        assertEquals(SanitizerFact(f, null, emptySet(), check), record.sanitizerFacts.single())
    }

    @Test
    fun `a source fact keeps its site and key patterns`() {
        val document = "- subject: {function: f}\n  sources: [{sourceKinds: [user-input], at: argument(1)}]\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        val source = record.sourceFacts.single()
        assertEquals(setOf(SourceKindId("user-input")), source.sourceKinds)
        assertEquals(Port.Argument(1), source.at)
        assertNull(source.keys)
    }

    @Test
    fun `a source fact at the result has no site`() {
        val document = "- subject: {function: f}\n  sources: [{sourceKinds: [user-input]}]\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        assertEquals(SourceFact(f, null, setOf(SourceKindId("user-input")), null, null), record.sourceFacts.single())
    }

    @Test
    fun `a returns fact and its flow facts come from one value unit`() {
        val document =
            "- subject: {function: f}\n  returns: str\n  propagation: [{from: argument(0), to: return}, {from: argument(1), to: return}]\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        assertEquals(ReturnsFact(f, null, ReturnKind.STR), record.returns.single())
        assertEquals(listOf(Port.Argument(0), Port.Argument(1)), record.flows.map { it.from })
        assertEquals(listOf<Port>(Port.Return, Port.Return), record.flows.map { it.to })
    }

    @Test
    fun `a characters fact comes from the value unit`() {
        val document =
            "- subject: {function: f}\n  returns: str\n  propagation: [{from: argument(0), to: return}]\n" +
                "  characters: {of: [argument(0)], within: \"[^/]\"}\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        val bound = CharactersFact(f, null, CharacterBound(setOf(Port.Argument(0)), CharacterClass("[^/]")))
        assertEquals(bound, record.characters.single())
    }

    @Test
    fun `a throws fact holds the whole class set`() {
        val document = "- subject: {function: f}\n  throws: [valueerror, \\jsonexception]\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        val classes = setOf(ClassSubject("valueerror"), ClassSubject("jsonexception"))
        assertEquals(ThrowsFact(f, null, classes), record.throws.single())
    }

    @Test
    fun `an empty throws section is a fact`() {
        val document = "- subject: {function: f}\n  throws: []\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        assertEquals(ThrowsFact(f, null, emptySet()), record.throws.single())
        assertEquals(record.throws, record.facts)
    }
}
