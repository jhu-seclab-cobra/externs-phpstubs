package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.CategoryMappingLoader
import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.GuardValue
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ProvenanceId
import edu.jhu.cobra.commons.phpmodels.SubjectModel
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import edu.jhu.cobra.commons.phpmodels.Vocabulary
import edu.jhu.cobra.commons.phpmodels.VocabularyLoader
import edu.jhu.cobra.commons.phpmodels.VulnClassId
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [StubResources] and the shipped taint document set it roots.
 *
 * - `opener resolves a shipped resource` — verifies a present path yields a stream under [StubResources.MODELS]
 * - `opener yields null for an absent path` — verifies absence is null, not a failure
 * - `opener accepts a root without trailing slash` — verifies root normalisation
 * - `taint set declares psalm's kinds and the input color` — verifies vocabulary and policy content
 * - `every taint entry is an unsigned model with exactly one taint section` — verifies the set's shape rule
 * - `sinks keep psalm's argument positions and kinds` — verifies dictionary and annotation sinks
 * - `sanitizers keep psalm's escapes including guarded ones` — verifies filter_var's five guarded entries
 * - `sources name the colored superglobals and annotated methods` — verifies the source entries
 * - `mapped load translates and discards per the consumer's table` — verifies a consumer-side mapping
 */
internal class StubResourcesTest {
    private val taint by lazy { DocumentSetLoader.load(StubResources.opener(StubResources.TAINT)) }

    private val models: Map<ModelSubject, SubjectModel> by lazy {
        taint.entries
            .filterIsInstance<SubjectModel>()
            .filter { it.guard == null }
            .associateBy { it.subject }
    }

    @Test
    fun `opener resolves a shipped resource`() {
        val stream = StubResources.opener(StubResources.MODELS).open("index.txt")
        assertNotNull(stream).close()
    }

    @Test
    fun `opener yields null for an absent path`() {
        assertNull(StubResources.opener(StubResources.TAINT).open("absent.yaml"))
    }

    @Test
    fun `opener accepts a root without trailing slash`() {
        val stream = StubResources.opener("/taint").open("vocabulary.yaml")
        assertNotNull(stream).close()
    }

    @Test
    fun `taint set declares psalm's kinds and the input color`() {
        val kinds =
            taint.vocabulary.vulnClasses.keys
                .map { it.id }
        assertEquals(15, kinds.size)
        assertTrue(kinds.containsAll(listOf("sql", "html", "shell", "eval", "include", "ssrf", "file", "header")))
        assertEquals(setOf(ProvenanceId("input")), taint.vocabulary.provenances.keys)
        val row = taint.policy.single()
        assertEquals(ProvenanceId("input"), row.origin)
        assertEquals(13, row.enables.size)
        assertTrue(VulnClassId("user_secret") !in row.enables)
    }

    @Test
    fun `every taint entry is an unsigned model with exactly one taint section`() {
        assertTrue(taint.entries.isNotEmpty())
        for (entry in taint.entries) {
            val model = entry as SubjectModel
            assertNull(model.signature, "$model.subject")
            val sections = listOfNotNull(model.body.sources, model.body.sinks, model.body.sanitizers)
            assertEquals(1, sections.size, "${model.subject}")
            assertNull(model.body.returns, "${model.subject}")
        }
    }

    @Test
    fun `sinks keep psalm's argument positions and kinds`() {
        assertEquals(
            listOf(Port.Argument(0) to "shell"),
            sinksOf(FunctionSubject("exec")),
        )
        assertEquals(listOf(Port.Argument(0) to "sql"), sinksOf(MethodSubject("mysqli", "query")))
        assertEquals(listOf(Port.Argument(2) to "sql"), sinksOf(FunctionSubject("pg_prepare")))
        assertEquals(listOf(Port.Argument(0) to "ssrf"), sinksOf(FunctionSubject("get_headers")))
    }

    @Test
    fun `sanitizers keep psalm's escapes including guarded ones`() {
        assertEquals(setOf("html", "has_quotes"), sanitizersOf(models.getValue(FunctionSubject("urlencode"))))
        assertEquals(setOf("sql"), sanitizersOf(models.getValue(MethodSubject("mysqli", "real_escape_string"))))
        val guarded =
            taint.entries
                .filterIsInstance<SubjectModel>()
                .filter { it.subject == FunctionSubject("filter_var") && it.guard != null }
        assertEquals(
            listOf(257L, 258L, 259L, 519L, 520L),
            guarded.map { (it.guard!!.value as GuardValue.IntValue).value },
        )
        assertTrue(guarded.all { it.guard!!.port == Port.Argument(1) })
        assertTrue(guarded.all { sanitizersOf(it) == setOf("html") })
        assertNull(models[FunctionSubject("filter_var")])
    }

    @Test
    fun `sources name the colored superglobals and annotated methods`() {
        for (name in listOf("_GET", "_POST", "_COOKIE", "_REQUEST")) {
            val model = models.getValue(VariableSubject(name))
            assertEquals(
                setOf(ProvenanceId("input")),
                model.body.sources!!
                    .single()
                    .provenance,
            )
        }
        assertNotNull(models[MethodSubject("Throwable", "getTraceAsString")])
        assertNotNull(models[MethodSubject("Exception", "__toString")])
    }

    @Test
    fun `mapped load translates and discards per the consumer's table`() {
        val context = StubResourcesTest::class.java.getResourceAsStream("/taint-context-test.yaml")!!.use(VocabularyLoader::load)
        val mapping = StubResourcesTest::class.java.getResourceAsStream("/taint-mapping-test.yaml")!!.use(CategoryMappingLoader::load)
        val mapped = DocumentSetLoader.load(StubResources.opener(StubResources.TAINT), context, mapping)
        assertEquals(Vocabulary.EMPTY, mapped.vocabulary)
        assertEquals(setOf(VulnClassId("sqli"), VulnClassId("xss")), mapped.policy.single().enables)
        assertEquals(ProvenanceId("user-input"), mapped.policy.single().origin)
        val bySubject = mapped.entries.filterIsInstance<SubjectModel>().groupBy { it.subject }
        assertNull(bySubject[FunctionSubject("exec")])
        assertEquals(setOf("xss"), sanitizersOf(bySubject.getValue(FunctionSubject("urlencode")).single()))
        assertEquals(listOf(Port.Argument(0) to "sqli"), sinksOf(bySubject.getValue(MethodSubject("mysqli", "query")).single()))
    }

    private fun sinksOf(subject: ModelSubject): List<Pair<Port.Argument, String>> = sinksOf(models.getValue(subject))

    private fun sinksOf(model: SubjectModel): List<Pair<Port.Argument, String>> = model.body.sinks!!.map { it.port to it.category.id }

    private fun sanitizersOf(model: SubjectModel): Set<String> =
        model.body.sanitizers!!
            .flatMap { decl -> decl.categories.map { it.id } }
            .toSet()
}
