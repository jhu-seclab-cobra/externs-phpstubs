package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.CategoryMappingLoader
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.Verification
import edu.jhu.cobra.commons.phpmodels.VulnClassId
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for [MountSequence]: set mounting, the corpus rules of the generated set, and failure classification.
 *
 * - `a corpus mount derives the extension from the document path` — verifies placement and the split suffix
 * - `extensionOf strips the document suffix and the split index only` — verifies the derivation over path shapes
 * - `a corpus rejects a variable subject` — verifies the first corpus rule
 * - `a corpus rejects an entry without a signature` — verifies the second corpus rule
 * - `a corpus rejects a conditional entry` — verifies the second corpus rule's condition half
 * - `a corpus rejects a subject declared by two documents` — verifies the third rule names both documents
 * - `a set without provenance mounts as the fallback or fails` — verifies bundled versus extension handling
 * - `a set with provenance mounts under its declared verification` — verifies the fallback is not applied
 * - `an absent manifest or document is not found` — verifies absence classification
 * - `a malformed document is invalid with its cause` — verifies invalidity classification
 * - `a manifest listing a document twice is invalid` — verifies the set's duplicate rule surfaces
 * - `later mounts decode against the accumulated vocabulary` — verifies vocabulary threading
 * - `an initial mount list seeds the accumulated vocabulary` — verifies extension over existing mounts
 * - `a mapped mount translates psalm names into the context vocabulary` — verifies the mapping is applied
 */
internal class MountTest {
    @Test
    fun `a corpus mount derives the extension from the document path`() {
        val mounts =
            corpus(
                "/models-test/",
            ).mount("/models-split/", StubResources.opener("/models-split/"), fallback = GEN, corpus = true).toList()
        val extensions = mounts.flatMap { it.entries }.associate { (entry, extension) -> entry.subject to extension }
        assertEquals("standard", extensions[FunctionSubject("strlen")])
        assertEquals("keyword", extensions[FunctionSubject("echo")])
        assertEquals("standard", extensions[FunctionSubject("split_one")])
        assertEquals(listOf(0, 1), mounts.map { it.position })
    }

    @Test
    fun `extensionOf strips the document suffix and the split index only`() {
        val expected =
            mapOf(
                "core.yaml" to "core",
                "standard/standard_1.yaml" to "standard",
                "language/standard_12.yaml" to "standard",
                "language/keyword.yaml" to "keyword",
                "database/ibm_db2.yaml" to "ibm_db2",
            )
        for ((path, extension) in expected) assertEquals(extension, MountSequence.extensionOf(path), path)
    }

    @Test
    fun `a corpus rejects a variable subject`() {
        val failure = assertFailsWith<StubIndexInvalidException> { corpus("/models-variable/") }
        assertTrue("variable" in failure.message!!)
    }

    @Test
    fun `a corpus rejects an entry without a signature`() {
        val failure = assertFailsWith<StubIndexInvalidException> { corpus("/models-nosignature/") }
        assertTrue("no signature" in failure.message!!)
    }

    @Test
    fun `a corpus rejects a conditional entry`() {
        val failure = assertFailsWith<StubIndexInvalidException> { corpus("/models-conditional/") }
        assertTrue("condition" in failure.message!!)
        assertTrue("cond_func" in failure.message!!)
    }

    @Test
    fun `a corpus rejects a subject declared by two documents`() {
        val failure = assertFailsWith<StubIndexInvalidException> { corpus("/models-duplicate/") }
        assertTrue("first.yaml" in failure.message!! && "second.yaml" in failure.message!!)
    }

    @Test
    fun `a set without provenance mounts as the fallback or fails`() {
        val manual = MountSequence().mount("/models-test/", StubResources.opener("/models-test/")).toList().single()
        assertEquals(Verification.MANUAL, manual.verification)
        assertTrue(manual.entries.all { it.second == null })
        val failure =
            assertFailsWith<StubIndexInvalidException> {
                MountSequence().mount("/models-test/", StubResources.opener("/models-test/"), fallback = null)
            }
        assertTrue("provenance" in failure.message!!)
    }

    @Test
    fun `a set with provenance mounts under its declared verification`() {
        val root = "/extension-generated/"
        val mount = MountSequence().mount(root, StubResources.opener(root)).toList().single()
        assertEquals(Verification.GENERATED, mount.verification)
    }

    @Test
    fun `an absent manifest or document is not found`() {
        assertTrue(assertFailsWith<StubIndexNotFoundException> { corpus("/absent-root/") }.message!!.endsWith("/absent-root/index.txt"))
        val missing = assertFailsWith<StubIndexNotFoundException> { corpus("/models-missing-file/") }
        assertTrue(missing.message!!.endsWith("/models-missing-file/absent.yaml"))
    }

    @Test
    fun `a malformed document is invalid with its cause`() {
        val failure = assertFailsWith<StubIndexInvalidException> { corpus("/models-invalid/") }
        assertTrue("/models-invalid/bad.yaml" in failure.message!!)
        assertNotNull(failure.cause)
    }

    @Test
    fun `a manifest listing a document twice is invalid`() {
        assertFailsWith<StubIndexInvalidException> { corpus("/models-doubled/") }
    }

    @Test
    fun `later mounts decode against the accumulated vocabulary`() {
        assertFailsWith<StubIndexInvalidException> { MountSequence().mount("mem:", TestSets.opener(*files(SINK))) }
        val sequence = MountSequence().mount("vocab:", TestSets.opener("index.txt" to "", "vocabulary.yaml" to TestSets.VOCABULARY))
        val mount = sequence.mount("mem:", TestSets.opener(*files(SINK))).toList().last()
        assertEquals(
            FunctionSubject("f"),
            mount.entries
                .single()
                .first.subject,
        )
    }

    @Test
    fun `an initial mount list seeds the accumulated vocabulary`() {
        val initial = listOf(TestSets.mount(0, Verification.MANUAL, "- subject: {function: g}\n  returns: str\n"))
        val mounts = MountSequence(initial).mount("mem:", TestSets.opener(*files(SINK))).toList()
        assertEquals(listOf(0, 1), mounts.map { it.position })
        assertEquals(
            FunctionSubject("f"),
            mounts
                .last()
                .entries
                .single()
                .first.subject,
        )
    }

    @Test
    fun `a mapped mount translates psalm names into the context vocabulary`() {
        val mapping = MountTest::class.java.getResourceAsStream(StubResources.PSALM_MAPPING)!!.use(CategoryMappingLoader::load)
        val mounts =
            MountSequence()
                .mount(StubResources.VOCABULARY, StubResources.opener(StubResources.VOCABULARY))
                .mount(StubResources.TAINT, StubResources.opener(StubResources.TAINT), mapping)
                .toList()
        val exec =
            mounts
                .last()
                .entries
                .map { it.first }
                .single { it.subject == FunctionSubject("exec") }
        assertEquals(
            VulnClassId("cmdi"),
            exec.body.sinks!!
                .single()
                .vulnClass,
        )
    }

    private fun files(document: String) = arrayOf("index.txt" to "models.yaml\n", "models.yaml" to document)

    private fun corpus(root: String): MountSequence = MountSequence().mount(root, StubResources.opener(root), fallback = GEN, corpus = true)

    private companion object {
        val GEN = Verification.GENERATED
        const val SINK = "- subject: {function: f}\n  sinks: [{port: argument(0), category: sqli}]\n"
    }
}
