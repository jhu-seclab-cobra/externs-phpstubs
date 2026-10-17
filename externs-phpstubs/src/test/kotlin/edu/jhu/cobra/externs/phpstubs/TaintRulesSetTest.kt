package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ArgumentCheck
import edu.jhu.cobra.commons.phpmodels.CharacterClass
import edu.jhu.cobra.commons.phpmodels.DeclaredType
import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelEntry
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.SourceKindId
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import edu.jhu.cobra.commons.phpmodels.VocabularyException
import edu.jhu.cobra.commons.phpmodels.VocabularyMappingLoader
import edu.jhu.cobra.commons.phpmodels.VulnTypeId
import edu.jhu.cobra.commons.value.BoolVal
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for the hand-maintained taint rules set rooted at [StubResources.TAINT_RULES].
 *
 * - `taint rules set loads only over the taint vocabulary` — verifies the set's names resolve through the taint set's context
 * - `taint rules set declares its own additions` — verifies the xpath kind, the external source kind, and the policy rows
 * - `every taint rules entry is an unsigned entry with exactly one taint section` — verifies the shape rule
 * - `no rules unit repeats a taint unit` — verifies each (subject, condition, section) differs from the taint set's
 * - `a taint rules sink over a taint subject widens psalm's ports` — verifies restated entries are strict supersets
 * - `sinks follow the Argus lists` — verifies representative sinks per vulnerability type
 * - `checks state type predicates and character checks` — verifies the type set, the class, and the covered kinds of representative checks
 * - `sanitizers and sources name the added escapes and source kinds` — verifies representative entries
 * - `the psalm mapping translates the additions` — verifies the bundled mapping covers xpath and external
 */
internal class TaintRulesSetTest {
    private val taint by lazy { DocumentSetLoader.load(StubResources.opener(StubResources.TAINT)) }
    private val rules by lazy { DocumentSetLoader.load(StubResources.opener(StubResources.TAINT_RULES), taint.vocabulary) }

    private val unconditional: Map<ModelSubject, ModelEntry> by lazy {
        rules.entries.filter { it.condition == null }.associateBy { it.subject }
    }

    @Test
    fun `taint rules set loads only over the taint vocabulary`() {
        assertFailsWith<VocabularyException> { DocumentSetLoader.load(StubResources.opener(StubResources.TAINT_RULES)) }
        assertTrue(rules.entries.isNotEmpty())
    }

    @Test
    fun `taint rules set declares its own additions`() {
        assertEquals(setOf(VulnTypeId("xpath")), rules.vocabulary.vulnTypes.keys)
        assertEquals(setOf(SourceKindId("external")), rules.vocabulary.sourceKinds.keys)
        val bySourceKind = rules.policy.associate { it.sourceKind to it.enables }
        assertEquals(setOf(VulnTypeId("xpath")), bySourceKind.getValue(SourceKindId("input")))
        val external = bySourceKind.getValue(SourceKindId("external"))
        assertTrue(external.containsAll(taint.policy.single().enables))
        assertTrue(VulnTypeId("xpath") in external)
    }

    @Test
    fun `every taint rules entry is an unsigned entry with exactly one taint section`() {
        for (entry in rules.entries) {
            assertNull(entry.signature, "${entry.subject}")
            assertNull(entry.body.returns, "${entry.subject}")
            val sections = listOfNotNull(entry.body.sources, entry.body.sinks, entry.body.sanitizers)
            assertEquals(1, sections.size, "${entry.subject}")
        }
    }

    @Test
    fun `no rules unit repeats a taint unit`() {
        val psalm = taint.entries.associateBy { it.subject to it.condition }
        for (entry in rules.entries) {
            val other = psalm[entry.subject to entry.condition] ?: continue
            entry.body.sinks?.let { assertNotEquals(other.body.sinks, it, "${entry.subject}") }
            entry.body.sanitizers?.let { assertNotEquals(other.body.sanitizers, it, "${entry.subject}") }
            entry.body.sources?.let { assertNotEquals(other.body.sources, it, "${entry.subject}") }
        }
    }

    @Test
    fun `a taint rules sink over a taint subject widens psalm's ports`() {
        val psalm = taint.entries.filter { it.body.sinks != null }.associateBy { it.subject }
        val restated = unconditional.values.filter { it.body.sinks != null && psalm[it.subject] != null }
        assertTrue(restated.isNotEmpty())
        for (entry in restated) {
            val base = psalm.getValue(entry.subject).body.sinks!!
            assertTrue(entry.body.sinks!!.containsAll(base), "${entry.subject}")
        }
        assertEquals(
            setOf(Port.Argument(0) to "html", Port.Argument(0) to "ssrf", Port.Argument(0) to "file", Port.Argument(0) to "unserialize"),
            sinksOf(FunctionSubject("readfile")),
        )
    }

    @Test
    fun `sinks follow the Argus lists`() {
        assertEquals(setOf(Port.Argument(4) to "shell"), sinksOf(FunctionSubject("mail")))
        assertEquals(setOf(Port.Argument(0) to "html"), sinksOf(FunctionSubject("echo")))
        assertEquals(setOf(Port.Argument(0) to "html", Port.Argument(1) to "html"), sinksOf(FunctionSubject("class_alias")))
        assertEquals(setOf(Port.Argument(0) to "eval"), sinksOf(FunctionSubject("eval")))
        assertEquals(setOf(Port.Argument(0) to "include"), sinksOf(FunctionSubject("require_once")))
        assertEquals(setOf(Port.Argument(1) to "callable"), sinksOf(FunctionSubject("usort")))
        assertEquals(setOf(Port.Argument(0) to "xpath"), sinksOf(MethodSubject("DOMXPath", "query")))
        assertEquals(setOf(Port.Argument(0) to "sql"), sinksOf(MethodSubject("SQLite3", "querySingle")))
        assertEquals(setOf(Port.Argument(1) to "ldap"), sinksOf(FunctionSubject("ldap_bind")))
        assertEquals(setOf(Port.Argument(0) to "unserialize"), sinksOf(MethodSubject("Phar", "__construct")))
        assertEquals(setOf(Port.Argument(0) to "file", Port.Argument(0) to "unserialize"), sinksOf(FunctionSubject("scandir")))
        assertNull(unconditional.getValue(FunctionSubject("curl_exec")).body.sinks)
        assertNull(unconditional[MethodSubject("SplFileObject", "fpassthru")])
    }

    @Test
    fun `sanitizers and sources name the added escapes and source kinds`() {
        assertEquals(setOf("shell"), sanitizersOf(FunctionSubject("escapeshellarg")))
        assertEquals(setOf("html"), sanitizersOf(FunctionSubject("htmlspecialchars")))
        assertEquals(setOf("file"), sanitizersOf(FunctionSubject("basename")))
        assertTrue(sanitizersOf(FunctionSubject("intval")).containsAll(listOf("sql", "html", "shell", "xpath")))
        assertEquals(setOf("input"), sourcesOf(VariableSubject("_SERVER")))
        assertEquals(setOf("input"), sourcesOf(FunctionSubject("getallheaders")))
        assertEquals(setOf("external"), sourcesOf(FunctionSubject("getenv")))
        assertEquals(setOf("external"), sourcesOf(MethodSubject("PDOStatement", "fetchAll")))
        assertNull(unconditional[VariableSubject("_GET")])
    }

    @Test
    fun `checks state type predicates and character checks`() {
        assertEquals(ArgumentCheck(Port.Argument(0), BoolVal(true), types = DeclaredType("int")), checkOf("is_int"))
        assertEquals(DeclaredType("int|float|string|bool"), checkOf("is_scalar").types)
        assertEquals(ArgumentCheck(Port.Argument(0), BoolVal(true), CharacterClass("[0-9]")), checkOf("ctype_digit"))
        assertTrue(sanitizersOf(FunctionSubject("ctype_digit")).containsAll(listOf("sql", "shell", "include")))
        assertFalse("shell" in sanitizersOf(FunctionSubject("is_numeric")))
        val numeric = assertNotNull(checkOf("is_numeric").within)
        assertTrue("-1.5E+3 INF\u000B".all { numeric.contains(it.code) })
        assertFalse(numeric.contains('x'.code))
    }

    @Test
    fun `the psalm mapping translates the additions`() {
        val context = DocumentSetLoader.load(StubResources.opener(StubResources.VOCABULARY)).vocabulary
        val mapping = TaintRulesSetTest::class.java.getResourceAsStream(StubResources.PSALM_MAPPING)!!.use(VocabularyMappingLoader::load)
        val mapped = DocumentSetLoader.load(StubResources.opener(StubResources.TAINT_RULES), context, mapping)
        val bySubject = mapped.entries.filter { it.condition == null }.associateBy { it.subject }
        assertEquals(setOf(Port.Argument(0) to "xpathi"), sinksOf(bySubject.getValue(MethodSubject("DOMXPath", "query"))))
        assertEquals(setOf(Port.Argument(0) to "xss"), sinksOf(bySubject.getValue(FunctionSubject("echo"))))
        assertEquals(setOf(Port.Argument(4) to "cmdi"), sinksOf(bySubject.getValue(FunctionSubject("mail"))))
        val getenv =
            bySubject
                .getValue(FunctionSubject("getenv"))
                .body.sources!!
                .single()
        assertEquals(setOf(SourceKindId("external-input")), getenv.sourceKinds)
        val external = mapped.policy.single { it.sourceKind == SourceKindId("external-input") }
        assertEquals(VulnType.entries.map { it.id }.toSet(), external.enables)
        assertNotNull(mapped.policy.singleOrNull { it.sourceKind == SourceKindId("user-input") })
    }

    private fun sinksOf(subject: ModelSubject): Set<Pair<Port.Argument, String>> = sinksOf(unconditional.getValue(subject))

    private fun sinksOf(entry: ModelEntry): Set<Pair<Port.Argument, String>> =
        entry.body.sinks!!
            .map { it.port to it.vulnType.id }
            .toSet()

    private fun checkOf(function: String): ArgumentCheck =
        assertNotNull(
            unconditional
                .getValue(FunctionSubject(function))
                .body.sanitizers
                ?.single()
                ?.check,
        )

    private fun sanitizersOf(subject: ModelSubject): Set<String> =
        unconditional
            .getValue(subject)
            .body.sanitizers!!
            .flatMap { decl -> decl.vulnTypes.map { it.id } }
            .toSet()

    private fun sourcesOf(subject: ModelSubject): Set<String> =
        unconditional
            .getValue(subject)
            .body.sources!!
            .flatMap { decl -> decl.sourceKinds.map { it.id } }
            .toSet()
}
