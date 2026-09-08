package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.VulnClassId
import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * Tests for the [VulnClass] enum: the compile-time names of the canonical danger categories.
 *
 * - `twelve constants carry the documented ids` — verifies the constants and their interned identifiers
 * - `the bundled vocabulary declares exactly the enum names` — verifies the vocabulary document against the enum
 */
internal class VulnClassTest {
    @Test
    fun `twelve constants carry the documented ids`() {
        val documented =
            listOf("sqli", "cmdi", "codei", "xss", "headeri", "ssrf", "pathtrav", "fileinc", "deser", "callablei", "ldapi", "xpathi")
        assertEquals(documented, VulnClass.entries.map { it.id.id })
        assertEquals(VulnClassId("sqli"), VulnClass.SQLI.id)
    }

    @Test
    fun `the bundled vocabulary declares exactly the enum names`() {
        val vocabulary = DocumentSetLoader.load(StubResources.opener(StubResources.VOCABULARY)).vocabulary
        assertEquals(VulnClass.entries.map { it.id }.toSet(), vocabulary.vulnClasses.keys)
    }
}
