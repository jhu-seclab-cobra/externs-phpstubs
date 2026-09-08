package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ArgPattern
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.Verification
import edu.jhu.cobra.commons.phpmodels.VulnClassId
import edu.jhu.cobra.commons.value.IntVal
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [Merge]: the fold of mounts into one statement per (subject, condition, unit) key.
 *
 * - `a manual statement outranks a later generated one` — verifies rank beats merge order
 * - `among equal ranks the later mount wins` — verifies merge order breaks a rank tie
 * - `statements under different conditions coexist` — verifies conditions partition a unit
 * - `a unit is replaced whole and other units stay in force` — verifies per-unit replacement
 * - `the extension follows the signature statement` — verifies a value override keeps the generated extension
 * - `a conditional entry declaring a signature fails the merge` — verifies the signature invariant
 * - `an empty mount list yields an empty merge` — verifies the degenerate input
 * - `vocabulary and policy accumulate over every mount` — verifies the merged vocabulary
 */
internal class MergeTest {
    private val generated =
        """
        - subject: {function: f}
          signature: {params: [{name: a, type: string}], returnType: int}
          sinks: [{port: argument(0), category: sqli}]
        """.trimIndent()

    @Test
    fun `a manual statement outranks a later generated one`() {
        val manual = TestSets.mount(0, Verification.MANUAL, "- subject: {function: f}\n  returns: str\n")
        val later = TestSets.mount(1, Verification.GENERATED, generated, extension = "standard")
        val record = Merge.of(listOf(manual, later)).functions.getValue(FunctionSubject("f"))
        assertEquals(ReturnKind.STR, record.returns.single().kind)
        assertEquals("standard", record.extension)
    }

    @Test
    fun `among equal ranks the later mount wins`() {
        val first = TestSets.mount(0, Verification.MANUAL, "- subject: {function: f}\n  returns: str\n")
        val second = TestSets.mount(1, Verification.MANUAL, "- subject: {function: f}\n  returns: num\n")
        val record = Merge.of(listOf(first, second)).functions.getValue(FunctionSubject("f"))
        assertEquals(ReturnKind.NUM, record.returns.single().kind)
    }

    @Test
    fun `statements under different conditions coexist`() {
        val document =
            """
            - subject: {function: f}
              returns: str
            - subject: {function: f}
              when: [_, 1]
              returns: num
            """.trimIndent()
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).functions.getValue(FunctionSubject("f"))
        assertEquals(listOf(null, ArgPattern(listOf(null, IntVal(1)))), record.returns.map { it.condition })
        assertEquals(listOf(ReturnKind.STR, ReturnKind.NUM), record.returns.map { it.kind })
    }

    @Test
    fun `a unit is replaced whole and other units stay in force`() {
        val base = TestSets.mount(0, Verification.GENERATED, generated, extension = "standard")
        val override =
            TestSets.mount(
                1,
                Verification.MANUAL,
                "- subject: {function: f}\n  returns: str\n  propagation: [{from: argument(0), to: return}]\n",
            )
        val record = Merge.of(listOf(base, override)).functions.getValue(FunctionSubject("f"))
        assertEquals(ReturnKind.STR, record.returns.single().kind)
        assertEquals(Port.Argument(0), record.flows.single().from)
        assertEquals(VulnClassId("sqli"), record.sinks.single().vulnClass)
        assertEquals("standard", record.extension)
    }

    @Test
    fun `the extension follows the signature statement`() {
        val base = TestSets.mount(0, Verification.GENERATED, generated, extension = "standard")
        val signed =
            TestSets.mount(
                1,
                Verification.MANUAL,
                "- subject: {function: f}\n  signature: {params: [{name: a, type: string}], returnType: string}\n" +
                    "  propagation: [{from: argument(0), to: return}]\n",
            )
        val record = Merge.of(listOf(base, signed)).functions.getValue(FunctionSubject("f"))
        assertNull(record.extension)
        assertEquals(ReturnKind.STR, record.returns.single().kind)
    }

    @Test
    fun `a conditional entry declaring a signature fails the merge`() {
        val document = "- subject: {function: f}\n  when: [1]\n  signature: {params: [{name: a, type: int}], returnType: int}\n"
        val mount = TestSets.mount(0, Verification.MANUAL, document)
        val failure = assertFailsWith<StubIndexInvalidException> { Merge.of(listOf(mount)) }
        assertTrue("signature" in failure.message!!)
    }

    @Test
    fun `an empty mount list yields an empty merge`() {
        val merge = Merge.of(emptyList())
        assertTrue(merge.records.isEmpty())
        assertTrue(merge.sinks.isEmpty())
        assertTrue(merge.vocabulary.vulnClasses.isEmpty())
    }

    @Test
    fun `vocabulary and policy accumulate over every mount`() {
        val first = TestSets.mount(0, Verification.MANUAL, "- subject: {function: f}\n  returns: str\n")
        val second = TestSets.mount(1, Verification.MANUAL, "- subject: {function: g}\n  returns: str\n", vocabulary = null)
        val merge = Merge.of(listOf(first, second))
        assertEquals(setOf(VulnClassId("sqli"), VulnClassId("xss")), merge.vocabulary.vulnClasses.keys)
        assertEquals(listOf(FunctionSubject("f"), FunctionSubject("g")), merge.functions.keys.toList())
    }
}
