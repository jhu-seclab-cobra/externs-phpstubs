package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.SourceKindId
import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * Tests for the [SourceKind] enum: the compile-time names of the canonical source kinds.
 *
 * - `three constants carry the documented ids` — verifies the constants and their interned identifiers
 * - `the bundled vocabulary declares exactly the enum names` — verifies the vocabulary document against the enum
 */
internal class SourceKindTest {
    @Test
    fun `three constants carry the documented ids`() {
        assertEquals(
            listOf("user-input", "external-input", "server-path"),
            SourceKind.entries.map { it.id.id },
        )
        assertEquals(SourceKindId("user-input"), SourceKind.USER_INPUT.id)
        assertEquals(SourceKindId("external-input"), SourceKind.EXTERNAL_INPUT.id)
        assertEquals(SourceKindId("server-path"), SourceKind.SERVER_PATH.id)
    }

    @Test
    fun `the bundled vocabulary declares exactly the enum names`() {
        val vocabulary = DocumentSetLoader.load(StubResources.opener(StubResources.VOCABULARY)).vocabulary
        assertEquals(SourceKind.entries.map { it.id }.toSet(), vocabulary.sourceKinds.keys)
    }
}
