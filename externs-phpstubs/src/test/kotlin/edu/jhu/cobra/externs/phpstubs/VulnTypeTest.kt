package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.VulnTypeId
import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * Tests for the [VulnType] enum: the compile-time names of the canonical danger categories.
 *
 * - `twelve constants carry the documented ids` — verifies the constants and their interned identifiers
 * - `the bundled vocabulary declares exactly the enum names` — verifies the vocabulary document against the enum
 */
internal class VulnTypeTest {
    @Test
    fun `twelve constants carry the documented ids`() {
        val documented =
            listOf("sqli", "cmdi", "codei", "xss", "headeri", "ssrf", "pathtrav", "fileinc", "deser", "callablei", "ldapi", "xpathi")
        assertEquals(documented, VulnType.entries.map { it.id.id })
        assertEquals(VulnTypeId("sqli"), VulnType.SQLI.id)
    }

    @Test
    fun `the bundled vocabulary declares exactly the enum names`() {
        val vocabulary = DocumentSetLoader.load(StubResources.opener(StubResources.VOCABULARY)).vocabulary
        assertEquals(VulnType.entries.map { it.id }.toSet(), vocabulary.vulnTypes.keys)
    }
}
