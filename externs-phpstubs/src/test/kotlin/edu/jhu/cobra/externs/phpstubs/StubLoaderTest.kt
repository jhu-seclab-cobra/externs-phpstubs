package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.Port
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for [StubLoader] discovery, decoding, attribution, and merge rules.
 * Fixtures: `/models-test/` (Gradle-generated manifest) and hand-manifested `/models-*` directories.
 *
 * - `loads every document listed by the manifest` — verifies entries from all four fixture documents are present
 * - `extension is the document file name` — verifies extension attribution per document
 * - `extension ignores the directory of a nested document` — verifies `language/keyword.yaml` yields `keyword`
 * - `extension strips numeric split suffix` — verifies `standard_1.yaml` yields `standard`
 * - `resource base without trailing slash is accepted` — verifies base normalisation
 * - `entries keep the decoded body` — verifies the propagation section survives loading
 * - `constant subject drops the leading namespace slash` — verifies the format's spelling rule reaches the key
 * - `missing manifest throws StubIndexNotFoundException` — verifies the error for an absent resource base
 * - `missing document error names the document` — verifies the message reports the document path, not the manifest
 * - `decode failure names the document and keeps the cause` — verifies format violations are wrapped with context
 * - `duplicate subject across documents names subject and both documents` — verifies the merge rule
 * - `generator entry is rejected` — verifies the corpus rule against generators
 * - `variable subject is rejected` — verifies the corpus rule against predefined variables
 * - `entry without signature is rejected` — verifies the corpus rule that every entry declares a signature
 */
internal class StubLoaderTest {
    private val registry: StubRegistry by lazy { StubLoader.loadAll("/models-test/") }

    @Test
    fun `loads every document listed by the manifest`() {
        assertEquals(
            setOf("define", "strlen", "substr", "sprintf", "echo"),
            registry.functions.keys.mapTo(HashSet()) { it.name },
        )
    }

    @Test
    fun `extension is the document file name`() {
        assertEquals("standard", registry.functions[FunctionSubject("strlen")]?.extension)
        assertEquals("core", registry.functions[FunctionSubject("define")]?.extension)
    }

    @Test
    fun `extension ignores the directory of a nested document`() {
        assertEquals("keyword", registry.functions[FunctionSubject("echo")]?.extension)
        assertEquals("scalar", registry.classes[ClassSubject("int")]?.extension)
    }

    @Test
    fun `extension strips numeric split suffix`() {
        val split = StubLoader.loadAll("/models-split/")
        assertEquals("standard", split.functions[FunctionSubject("split_one")]?.extension)
        assertEquals("standard", split.functions[FunctionSubject("split_two")]?.extension)
    }

    @Test
    fun `resource base without trailing slash is accepted`() {
        assertEquals(registry, StubLoader.loadAll("/models-test"))
    }

    @Test
    fun `entries keep the decoded body`() {
        val substr = assertNotNull(registry.functions[FunctionSubject("substr")])
        val flows = assertNotNull(substr.model.body.propagation)
        assertEquals(listOf(Port.Argument(0) to Port.Return), flows.map { it.from to it.to })
    }

    @Test
    fun `constant subject drops the leading namespace slash`() {
        assertEquals("7", registry.constants[ConstantSubject("SLASHED_CONST")]?.typedSignature?.value)
    }

    @Test
    fun `missing manifest throws StubIndexNotFoundException`() {
        val failure = assertFailsWith<StubIndexNotFoundException> { StubLoader.loadAll("/nonexistent-path/") }
        assertEquals("Stub resource not found: /nonexistent-path/index.txt", failure.message)
    }

    @Test
    fun `missing document error names the document`() {
        val failure = assertFailsWith<StubIndexNotFoundException> { StubLoader.loadAll("/models-missing-file/") }
        assertEquals("Stub resource not found: /models-missing-file/absent.yaml", failure.message)
    }

    @Test
    fun `decode failure names the document and keeps the cause`() {
        val failure = assertFailsWith<StubIndexInvalidException> { StubLoader.loadAll("/models-invalid/") }
        val reason = assertNotNull(failure.message)
        assertTrue("/models-invalid/bad.yaml" in reason, "expected the document path, was: $reason")
        assertIs<IllegalArgumentException>(failure.cause)
    }

    @Test
    fun `duplicate subject across documents names subject and both documents`() {
        val failure = assertFailsWith<StubIndexInvalidException> { StubLoader.loadAll("/models-duplicate/") }
        val reason = assertNotNull(failure.message)
        assertTrue("dup_func" in reason, "expected the subject name, was: $reason")
        assertTrue("/models-duplicate/first.yaml" in reason, "expected first.yaml, was: $reason")
        assertTrue("/models-duplicate/second.yaml" in reason, "expected second.yaml, was: $reason")
    }

    @Test
    fun `generator entry is rejected`() {
        val failure = assertFailsWith<StubIndexInvalidException> { StubLoader.loadAll("/models-generator/") }
        val reason = assertNotNull(failure.message)
        assertTrue("getters" in reason, "expected the generator name, was: $reason")
    }

    @Test
    fun `variable subject is rejected`() {
        val failure = assertFailsWith<StubIndexInvalidException> { StubLoader.loadAll("/models-variable/") }
        val reason = assertNotNull(failure.message)
        assertTrue("/models-variable/var.yaml" in reason, "expected the document path, was: $reason")
    }

    @Test
    fun `entry without signature is rejected`() {
        val failure = assertFailsWith<StubIndexInvalidException> { StubLoader.loadAll("/models-nosignature/") }
        val reason = assertNotNull(failure.message)
        assertTrue("no_signature" in reason, "expected the subject name, was: $reason")
    }
}
