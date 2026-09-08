package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.Verification
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for [MountSequence]: set mounting, the corpus rules of the generated set, and failure classification.
 *
 * - `a corpus mount derives the extension from the document path` — verifies placement and the split suffix
 * - `a corpus rejects a variable subject` — verifies the first corpus rule
 * - `a corpus rejects an entry without a signature` — verifies the second corpus rule
 * - `a corpus rejects a subject declared by two documents` — verifies the third rule names both documents
 * - `a set without provenance mounts as the fallback or fails` — verifies bundled versus extension handling
 * - `an absent manifest or document is not found` — verifies absence classification
 * - `a malformed document is invalid with its cause` — verifies invalidity classification
 * - `a manifest listing a document twice is invalid` — verifies the set's duplicate rule surfaces
 * - `later mounts decode against the accumulated vocabulary` — verifies vocabulary threading
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
        assertEquals("standard", MountSequence.extensionOf("language/standard_12.yaml"))
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
        val sink = "- subject: {function: f}\n  sinks: [{port: argument(0), category: sqli}]\n"
        assertFailsWith<StubIndexInvalidException> { MountSequence().mount("mem:", TestSets.opener(*files(sink))) }
        val sequence = MountSequence().mount("vocab:", TestSets.opener("index.txt" to "", "vocabulary.yaml" to TestSets.VOCABULARY))
        val mount = sequence.mount("mem:", TestSets.opener(*files(sink))).toList().last()
        assertEquals(
            FunctionSubject("f"),
            mount.entries
                .single()
                .first.subject,
        )
    }

    private fun files(document: String) = arrayOf("index.txt" to "models.yaml\n", "models.yaml" to document)

    private fun corpus(root: String): MountSequence = MountSequence().mount(root, StubResources.opener(root), fallback = GEN, corpus = true)

    private companion object {
        val GEN = Verification.GENERATED
    }
}
