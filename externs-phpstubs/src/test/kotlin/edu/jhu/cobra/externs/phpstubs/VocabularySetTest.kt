package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.Verification
import edu.jhu.cobra.commons.phpmodels.VocabularyMappingLoader
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for the canonical vocabulary set rooted at [StubResources.VOCABULARY].
 *
 * - `the vocabulary set ships no model document` — verifies the comment-only manifest yields no entry
 * - `the vocabulary set is manually verified` — verifies the set's provenance
 * - `the policy enables every vulnerability type under the two input source kinds` — verifies their rows of the matrix
 * - `the server path source kind enables every type except scheme injection` — verifies the third row
 * - `the psalm mapping leaves no psalm name in a mapped set` — verifies mapping totality and the discarded kinds
 */
internal class VocabularySetTest {
    private val set by lazy { DocumentSetLoader.load(StubResources.opener(StubResources.VOCABULARY)) }

    @Test
    fun `the vocabulary set ships no model document`() {
        assertTrue(set.entries.isEmpty())
        assertTrue(set.documents.isEmpty())
    }

    @Test
    fun `the vocabulary set is manually verified`() {
        assertEquals(Verification.MANUAL, assertNotNull(set.provenance).verification)
    }

    @Test
    fun `the policy enables every vulnerability type under the two input source kinds`() {
        val all = VulnType.entries.map { it.id }.toSet()
        assertEquals(SourceKind.entries.map { it.id }.toSet(), set.policy.map { it.sourceKind }.toSet())
        for (row in set.policy.filter { it.sourceKind != SourceKind.SERVER_PATH.id }) {
            assertEquals(all, row.enables, row.sourceKind.id)
        }
    }

    @Test
    fun `the server path source kind enables every type except scheme injection`() {
        val row = set.policy.single { it.sourceKind == SourceKind.SERVER_PATH.id }
        assertEquals(VulnType.entries.map { it.id }.toSet() - VulnType.SCHEMEI.id, row.enables)
    }

    @Test
    fun `the psalm mapping leaves no psalm name in a mapped set`() {
        val mapping = VocabularySetTest::class.java.getResourceAsStream(StubResources.PSALM_MAPPING)!!.use(VocabularyMappingLoader::load)
        val canonical = VulnType.entries.map { it.id }.toSet()
        val sourceKinds = SourceKind.entries.map { it.id }.toSet()
        for (root in listOf(StubResources.TAINT, StubResources.TAINT_RULES)) {
            val mapped = DocumentSetLoader.load(StubResources.opener(root), set.vocabulary, mapping)
            for (entry in mapped.entries) {
                val vulnTypes =
                    entry.body.sinks
                        .orEmpty()
                        .map { it.vulnType } +
                        entry.body.sanitizers
                            .orEmpty()
                            .flatMap { it.vulnTypes }
                assertTrue(canonical.containsAll(vulnTypes), "${entry.subject}")
                assertTrue(
                    sourceKinds.containsAll(
                        entry.body.sources
                            .orEmpty()
                            .flatMap { it.sourceKinds },
                    ),
                    "${entry.subject}",
                )
            }
            assertTrue(mapped.policy.all { it.sourceKind in sourceKinds && canonical.containsAll(it.enables) }, root)
        }
    }
}
