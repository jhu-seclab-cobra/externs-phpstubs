package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.CategoryMappingLoader
import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelEntry
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.OriginId
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import edu.jhu.cobra.commons.phpmodels.Vocabulary
import edu.jhu.cobra.commons.phpmodels.VulnClassId
import edu.jhu.cobra.commons.value.IntVal
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for the generated taint document set rooted at [StubResources.TAINT].
 *
 * - `taint set declares psalm's kinds and the input color` — verifies vocabulary and policy content
 * - `taint set names its producer` — verifies the provenance document
 * - `every taint entry is an unsigned entry with exactly one taint section` — verifies the set's shape rule
 * - `sinks keep psalm's argument positions and kinds` — verifies dictionary and annotation sinks
 * - `sanitizers keep psalm's escapes including conditional ones` — verifies filter_var's five conditional entries
 * - `sources name the colored superglobals and annotated methods` — verifies the source entries
 * - `the psalm mapping translates the taint set into the canonical vocabulary` — verifies the bundled mapping
 */
internal class TaintSetTest {
    private val taint by lazy { DocumentSetLoader.load(StubResources.opener(StubResources.TAINT)) }

    private val unconditional: Map<ModelSubject, ModelEntry> by lazy {
        taint.entries.filter { it.condition == null }.associateBy { it.subject }
    }

    @Test
    fun `taint set declares psalm's kinds and the input color`() {
        val kinds =
            taint.vocabulary.vulnClasses.keys
                .map { it.id }
        assertEquals(15, kinds.size)
        assertTrue(kinds.containsAll(listOf("sql", "html", "shell", "eval", "include", "ssrf", "file", "header")))
        assertEquals(setOf(OriginId("input")), taint.vocabulary.origins.keys)
        val row = taint.policy.single()
        assertEquals(OriginId("input"), row.origin)
        assertEquals(13, row.enables.size)
        assertTrue(VulnClassId("user_secret") !in row.enables)
    }

    @Test
    fun `taint set names its producer`() {
        assertEquals("tools/extract_taint.py over vimeo/psalm 5.6.0", assertNotNull(taint.provenance).producer)
    }

    @Test
    fun `every taint entry is an unsigned entry with exactly one taint section`() {
        assertTrue(taint.entries.isNotEmpty())
        for (entry in taint.entries) {
            assertNull(entry.signature, "${entry.subject}")
            val sections = listOfNotNull(entry.body.sources, entry.body.sinks, entry.body.sanitizers)
            assertEquals(1, sections.size, "${entry.subject}")
            assertNull(entry.body.returns, "${entry.subject}")
        }
    }

    @Test
    fun `sinks keep psalm's argument positions and kinds`() {
        assertEquals(listOf(Port.Argument(0) to "shell"), sinksOf(FunctionSubject("exec")))
        assertEquals(listOf(Port.Argument(0) to "sql"), sinksOf(MethodSubject("mysqli", "query")))
        assertEquals(listOf(Port.Argument(2) to "sql"), sinksOf(FunctionSubject("pg_prepare")))
        assertEquals(listOf(Port.Argument(0) to "ssrf"), sinksOf(FunctionSubject("get_headers")))
    }

    @Test
    fun `sanitizers keep psalm's escapes including conditional ones`() {
        assertEquals(setOf("html", "has_quotes"), sanitizersOf(unconditional.getValue(FunctionSubject("urlencode"))))
        assertEquals(setOf("sql"), sanitizersOf(unconditional.getValue(MethodSubject("mysqli", "real_escape_string"))))
        val conditional = taint.entries.filter { it.subject == FunctionSubject("filter_var") && it.condition != null }
        assertEquals(
            listOf(257L, 258L, 259L, 519L, 520L),
            conditional.map { (it.condition!!.expected[1] as IntVal).core },
        )
        assertTrue(conditional.all { it.condition!!.positions == listOf(1) })
        assertTrue(conditional.all { sanitizersOf(it) == setOf("html") })
        assertNull(unconditional[FunctionSubject("filter_var")])
    }

    @Test
    fun `sources name the colored superglobals and annotated methods`() {
        for (name in listOf("_GET", "_POST", "_COOKIE", "_REQUEST")) {
            val entry = unconditional.getValue(VariableSubject(name))
            assertEquals(
                setOf(OriginId("input")),
                entry.body.sources!!
                    .single()
                    .origin,
            )
        }
        assertNotNull(unconditional[MethodSubject("Throwable", "getTraceAsString")])
        assertNotNull(unconditional[MethodSubject("Exception", "__toString")])
    }

    @Test
    fun `the psalm mapping translates the taint set into the canonical vocabulary`() {
        val context = DocumentSetLoader.load(StubResources.opener(StubResources.VOCABULARY)).vocabulary
        val mapping = TaintSetTest::class.java.getResourceAsStream(StubResources.PSALM_MAPPING)!!.use(CategoryMappingLoader::load)
        val mapped = DocumentSetLoader.load(StubResources.opener(StubResources.TAINT), context, mapping)
        assertEquals(Vocabulary.EMPTY, mapped.vocabulary)
        assertEquals(OriginId("user-input"), mapped.policy.single().origin)
        val enables = mapped.policy.single().enables
        assertTrue(VulnClass.entries.map { it.id }.containsAll(enables) && VulnClassId("xss") in enables)
        val bySubject = mapped.entries.groupBy { it.subject }
        assertEquals(listOf(Port.Argument(0) to "cmdi"), sinksOf(bySubject.getValue(FunctionSubject("exec")).single()))
        assertEquals(setOf("xss"), sanitizersOf(bySubject.getValue(FunctionSubject("urlencode")).single()))
        assertEquals(listOf(Port.Argument(0) to "sqli"), sinksOf(bySubject.getValue(MethodSubject("mysqli", "query")).single()))
    }

    private fun sinksOf(subject: ModelSubject): List<Pair<Port.Argument, String>> = sinksOf(unconditional.getValue(subject))

    private fun sinksOf(entry: ModelEntry): List<Pair<Port.Argument, String>> = entry.body.sinks!!.map { it.port to it.vulnClass.id }

    private fun sanitizersOf(entry: ModelEntry): Set<String> =
        entry.body.sanitizers!!
            .flatMap { decl -> decl.categories.map { it.id } }
            .toSet()
}
