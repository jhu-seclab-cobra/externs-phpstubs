package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ArgPattern
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.Verification
import edu.jhu.cobra.commons.phpmodels.VulnTypeId
import edu.jhu.cobra.commons.value.IntVal
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [Merge]: the fold of mounts into one statement per (subject, condition, unit) key.
 *
 * - `a manual statement outranks a later generated one` — verifies rank beats merge order
 * - `among equal ranks the later mount wins` — verifies merge order breaks a rank tie
 * - `within one set the later document wins the same key` — verifies document order inside a set
 * - `statements under different conditions coexist` — verifies conditions partition a unit
 * - `a conditional statement never replaces an unconditional one across ranks` — verifies the partition holds under rank
 * - `a unit is replaced whole and other units stay in force` — verifies per-unit replacement
 * - `a value statement without characters replaces the bound` — verifies characters belong to the value unit
 * - `a throws statement is replaced only by another throws statement` — verifies the throws unit
 * - `the extension follows the signature statement` — verifies a value override keeps the generated extension
 * - `a signature-only statement yields a record without facts` — verifies a declaration is a record
 * - `a conditional entry declaring a signature fails the merge` — verifies the signature invariant
 * - `an empty mount list yields an empty merge` — verifies the degenerate input
 * - `vocabulary and policy accumulate over every mount` — verifies the merged vocabulary
 * - `each subject appears in exactly one kind map` — verifies the kind maps partition the records
 * - `fact lists follow record order then first-statement order` — verifies enumeration determinism
 * - `equal mount lists merge into equal records` — verifies the fold is a function of its input
 */
internal class MergeTest {
    private val f = FunctionSubject("f")

    private val generated =
        """
        - subject: {function: f}
          signature: {params: [{name: a, type: string}], returnType: int}
          sinks: [{port: argument(0), vulnType: sqli}]
        """.trimIndent()

    @Test
    fun `a manual statement outranks a later generated one`() {
        val manual = TestSets.mount(0, Verification.MANUAL, "- subject: {function: f}\n  returns: str\n")
        val later = TestSets.mount(1, Verification.GENERATED, generated, extension = "standard")
        val record = Merge.of(listOf(manual, later)).functions.getValue(f)
        assertEquals(ReturnKind.STR, record.returns.single().kind)
        assertEquals("standard", record.extension)
    }

    @Test
    fun `among equal ranks the later mount wins`() {
        val first = TestSets.mount(0, Verification.MANUAL, "- subject: {function: f}\n  returns: str\n")
        val second = TestSets.mount(1, Verification.MANUAL, "- subject: {function: f}\n  returns: num\n")
        val record = Merge.of(listOf(first, second)).functions.getValue(f)
        assertEquals(ReturnKind.NUM, record.returns.single().kind)
    }

    @Test
    fun `within one set the later document wins the same key`() {
        val root = "/set-two-documents/"
        val merge = Merge.of(MountSequence().mount(root, StubResources.opener(root)).toList())
        assertEquals(
            ReturnKind.NUM,
            merge.functions
                .getValue(FunctionSubject("twice"))
                .returns
                .single()
                .kind,
        )
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
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).functions.getValue(f)
        assertEquals(listOf(null, ArgPattern(listOf(null, IntVal(1)))), record.returns.map { it.condition })
        assertEquals(listOf(ReturnKind.STR, ReturnKind.NUM), record.returns.map { it.kind })
    }

    @Test
    fun `a conditional statement never replaces an unconditional one across ranks`() {
        val valued =
            """
            - subject: {function: f}
              signature: {params: [{name: a, type: string}], returnType: int}
              propagation: [{from: argument(0), to: return}]
              sinks: [{port: argument(0), vulnType: sqli}]
            """.trimIndent()
        val base = TestSets.mount(0, Verification.GENERATED, valued, extension = "standard")
        val conditional = TestSets.mount(1, Verification.MANUAL, "- subject: {function: f}\n  when: [1]\n  returns: num\n")
        val record = Merge.of(listOf(base, conditional)).functions.getValue(f)
        val condition = ArgPattern(listOf(IntVal(1)))
        assertEquals(listOf(null, condition), record.returns.map { it.condition })
        assertEquals(listOf(ReturnKind.NUM, ReturnKind.NUM), record.returns.map { it.kind })
        assertEquals(listOf(null), record.flows.map { it.condition })
        assertEquals(VulnTypeId("sqli"), record.sinkFacts.single().vulnType)
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
        val record = Merge.of(listOf(base, override)).functions.getValue(f)
        assertEquals(ReturnKind.STR, record.returns.single().kind)
        assertEquals(Port.Argument(0), record.flows.single().from)
        assertEquals(VulnTypeId("sqli"), record.sinkFacts.single().vulnType)
        assertEquals("standard", record.extension)
    }

    @Test
    fun `a value statement without characters replaces the bound`() {
        val document =
            "- subject: {function: f}\n  returns: str\n  propagation: [{from: argument(0), to: return}]\n" +
                "  characters: {of: [argument(0)]}\n"
        val base = TestSets.mount(0, Verification.GENERATED, document)
        val bounded = Merge.of(listOf(base)).functions.getValue(f)
        assertEquals(
            setOf(Port.Argument(0)),
            bounded.characters
                .single()
                .bound.of,
        )
        val value = TestSets.mount(1, Verification.MANUAL, "- subject: {function: f}\n  returns: str\n")
        val replaced = Merge.of(listOf(base, value)).functions.getValue(f)
        assertTrue(replaced.characters.isEmpty())
        assertTrue(replaced.flows.isEmpty())
    }

    @Test
    fun `a throws statement is replaced only by another throws statement`() {
        val base = TestSets.mount(0, Verification.GENERATED, "$generated\n  throws: [valueerror]\n", extension = "standard")
        val value = TestSets.mount(1, Verification.MANUAL, "- subject: {function: f}\n  returns: str\n")
        val kept = Merge.of(listOf(base, value)).functions.getValue(f)
        assertEquals(setOf(ClassSubject("valueerror")), kept.throws.single().classes)
        val none = TestSets.mount(2, Verification.MANUAL, "- subject: {function: f}\n  throws: []\n")
        val replaced = Merge.of(listOf(base, value, none)).functions.getValue(f)
        assertEquals(emptySet(), replaced.throws.single().classes)
        assertEquals(ReturnKind.STR, replaced.returns.single().kind)
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
        val record = Merge.of(listOf(base, signed)).functions.getValue(f)
        assertNull(record.extension)
        assertEquals(ReturnKind.STR, record.returns.single().kind)
    }

    @Test
    fun `a signature-only statement yields a record without facts`() {
        val document = "- subject: {class: K}\n  signature: {classifier: class}\n"
        val record = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document))).classes.getValue(ClassSubject("K"))
        assertNotNull(record.signature)
        assertTrue(record.facts.isEmpty())
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
        assertTrue(merge.sinkFacts.isEmpty())
        assertTrue(merge.vocabulary.vulnTypes.isEmpty())
    }

    @Test
    fun `vocabulary and policy accumulate over every mount`() {
        val first = TestSets.mount(0, Verification.MANUAL, "- subject: {function: f}\n  returns: str\n")
        val second = TestSets.mount(1, Verification.MANUAL, "- subject: {function: g}\n  returns: str\n", vocabulary = null)
        val merge = Merge.of(listOf(first, second))
        assertEquals(setOf(VulnTypeId("sqli"), VulnTypeId("xss")), merge.vocabulary.vulnTypes.keys)
        assertEquals(listOf(f, FunctionSubject("g")), merge.functions.keys.toList())
    }

    @Test
    fun `each subject appears in exactly one kind map`() {
        val document =
            """
            - subject: {function: f}
              returns: str
            - subject: {class: K}
              signature: {classifier: class}
            - subject: {constant: C}
              signature: {type: int, value: '1'}
            """.trimIndent()
        val merge = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document)))
        assertEquals(setOf<Any>(f), merge.functions.keys)
        assertEquals(setOf<Any>(ClassSubject("K")), merge.classes.keys)
        assertEquals(setOf<Any>(ConstantSubject("C")), merge.constants.keys)
        assertEquals(3, merge.records.size)
        assertTrue(merge.methods.isEmpty() && merge.variables.isEmpty())
    }

    @Test
    fun `fact lists follow record order then first-statement order`() {
        val document =
            """
            - subject: {function: g}
              when: [1]
              sinks: [{port: argument(0), vulnType: xss}]
            - subject: {function: f}
              sinks: [{port: argument(0), vulnType: sqli}]
            - subject: {function: g}
              sinks: [{port: argument(0), vulnType: sqli}]
            """.trimIndent()
        val merge = Merge.of(listOf(TestSets.mount(0, Verification.MANUAL, document)))
        val g = FunctionSubject("g")
        assertEquals(listOf(g, g, f), merge.sinkFacts.map { it.owner })
        assertEquals(
            listOf(ArgPattern(listOf(IntVal(1))), null),
            merge.functions
                .getValue(g)
                .sinkFacts
                .map { it.condition },
        )
    }

    @Test
    fun `equal mount lists merge into equal records`() {
        val mounts = {
            listOf(
                TestSets.mount(0, Verification.GENERATED, generated, extension = "standard"),
                TestSets.mount(1, Verification.MANUAL, "- subject: {function: f}\n  returns: str\n"),
            )
        }
        assertEquals(Merge.of(mounts()).records, Merge.of(mounts()).records)
    }
}
