package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.OriginId
import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * Tests for the [Origin] enum: the compile-time names of the canonical origin colors.
 *
 * - `two constants carry the documented ids` — verifies the constants and their interned identifiers
 * - `the bundled vocabulary declares exactly the enum names` — verifies the vocabulary document against the enum
 */
internal class OriginTest {
    @Test
    fun `two constants carry the documented ids`() {
        assertEquals(
            listOf("user-input", "external-input"),
            Origin.entries.map { it.id.id },
        )
        assertEquals(OriginId("user-input"), Origin.USER_INPUT.id)
        assertEquals(OriginId("external-input"), Origin.EXTERNAL_INPUT.id)
    }

    @Test
    fun `the bundled vocabulary declares exactly the enum names`() {
        val vocabulary = DocumentSetLoader.load(StubResources.opener(StubResources.VOCABULARY)).vocabulary
        assertEquals(Origin.entries.map { it.id }.toSet(), vocabulary.origins.keys)
    }
}
