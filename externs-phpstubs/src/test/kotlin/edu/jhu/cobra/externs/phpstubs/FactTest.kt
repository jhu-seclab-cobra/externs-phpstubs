package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ArgPattern
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.OriginId
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.Verification
import edu.jhu.cobra.commons.phpmodels.VulnClassId
import edu.jhu.cobra.commons.value.BoolVal
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

/**
 * Tests for the [Fact] kinds a merged record exposes: each carries its owner and the condition of its entry.
 *
 * - `an unconditional entry yields facts without a condition` — verifies the null condition
 * - `a conditional entry tags every fact with its pattern` — verifies condition propagation per fact kind
 * - `a source fact keeps its site and key patterns` — verifies the by-reference source shape
 * - `a source fact at the result has no site` — verifies the result-site source shape
 * - `a returns fact and its flow facts come from one value unit` — verifies the classification and the ports
 */
internal class FactTest {
    private val f = FunctionSubject("f")

    @Test
    fun `an unconditional entry yields facts without a condition`() {
        val document = "- subject: {function: f}\n  sinks: [{port: argument(1), category: xss}]\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        assertEquals(SinkFact(f, null, Port.Argument(1), VulnClassId("xss")), record.sinks.single())
    }

    @Test
    fun `a conditional entry tags every fact with its pattern`() {
        val document =
            """
            - subject: {function: f}
              when: [true]
              sanitizers: [{categories: [sqli]}]
              returns: str
              propagation: [{from: argument(0), to: return}]
            """.trimIndent()
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        val condition = ArgPattern(listOf(BoolVal(true)))
        assertEquals(SanitizerFact(f, condition, setOf(VulnClassId("sqli"))), record.sanitizers.single())
        assertEquals(condition, record.returns.single().condition)
        assertEquals(FlowFact(f, condition, Port.Argument(0), Port.Return), record.flows.single())
    }

    @Test
    fun `a source fact keeps its site and key patterns`() {
        val document = "- subject: {function: f}\n  sources: [{provenance: [user-input], at: argument(1)}]\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        val source = record.sources.single()
        assertEquals(setOf(OriginId("user-input")), source.origins)
        assertEquals(Port.Argument(1), source.at)
        assertNull(source.keys)
    }

    @Test
    fun `a source fact at the result has no site`() {
        val document = "- subject: {function: f}\n  sources: [{provenance: [user-input]}]\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).records.getValue(f)
        assertEquals(SourceFact(f, null, setOf(OriginId("user-input")), null, null), record.sources.single())
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
}
