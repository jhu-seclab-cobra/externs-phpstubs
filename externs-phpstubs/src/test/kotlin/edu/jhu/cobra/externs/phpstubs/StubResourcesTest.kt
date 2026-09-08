package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.Verification
import edu.jhu.cobra.commons.phpmodels.Vocabulary
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNotSame
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [StubResources]: the bundled roots and the opener over a root. The shipped sets themselves:
 * [TaintSetTest], [TaintRulesSetTest], [ValueRulesSetTest], [VocabularySetTest], [ManualDeclarationsTest].
 *
 * - `roots name the bundled set directories` — verifies the six constants against the documented layout
 * - `opener resolves a shipped resource` — verifies a present path yields a stream under [StubResources.MODELS]
 * - `opener yields null for an absent path` — verifies absence is null, not a failure
 * - `opener accepts a root without trailing slash` — verifies root normalisation
 * - `opener yields a fresh stream per call` — verifies two opens of one path are distinct streams
 * - `every shipped set declares its provenance` — verifies producer and verification kind per set
 */
internal class StubResourcesTest {
    @Test
    fun `roots name the bundled set directories`() {
        assertEquals("/models/", StubResources.MODELS)
        assertEquals("/value-rules/", StubResources.VALUE_RULES)
        assertEquals("/vocabulary/", StubResources.VOCABULARY)
        assertEquals("/taint/", StubResources.TAINT)
        assertEquals("/taint-rules/", StubResources.TAINT_RULES)
        assertEquals("/vocabulary/psalm-mapping.yaml", StubResources.PSALM_MAPPING)
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
    fun `opener yields a fresh stream per call`() {
        val opener = StubResources.opener(StubResources.TAINT)
        val first = assertNotNull(opener.open("index.txt"))
        val second = assertNotNull(opener.open("index.txt"))
        assertNotSame(first, second)
        first.close()
        second.close()
    }

    @Test
    fun `every shipped set declares its provenance`() {
        val expected =
            mapOf(
                StubResources.MODELS to Verification.GENERATED,
                StubResources.VALUE_RULES to Verification.MANUAL,
                StubResources.VOCABULARY to Verification.MANUAL,
                StubResources.TAINT to Verification.GENERATED,
                StubResources.TAINT_RULES to Verification.MANUAL,
            )
        val taintVocabulary = DocumentSetLoader.load(StubResources.opener(StubResources.TAINT)).vocabulary
        for ((root, verification) in expected) {
            val context = if (root == StubResources.TAINT_RULES) taintVocabulary else Vocabulary.EMPTY
            val provenance = assertNotNull(DocumentSetLoader.load(StubResources.opener(root), context).provenance, root)
            assertEquals(verification, provenance.verification, root)
            assertTrue(provenance.producer.isNotBlank(), root)
        }
    }
}
