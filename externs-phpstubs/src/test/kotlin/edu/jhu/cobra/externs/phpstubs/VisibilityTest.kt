package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * Tests for [Visibility] enum.
 *
 * - `enum has exactly three entries` — verifies PUBLIC, PROTECTED, PRIVATE are the only members
 * - `valueOf PUBLIC returns PUBLIC` — verifies valueOf round-trip for PUBLIC
 * - `valueOf PROTECTED returns PROTECTED` — verifies valueOf round-trip for PROTECTED
 * - `valueOf PRIVATE returns PRIVATE` — verifies valueOf round-trip for PRIVATE
 */
internal class VisibilityTest {

    @Test
    fun `enum has exactly three entries`() {
        assertEquals(3, Visibility.entries.size)
        assertEquals(
            setOf(Visibility.PUBLIC, Visibility.PROTECTED, Visibility.PRIVATE),
            Visibility.entries.toSet(),
        )
    }

    @Test
    fun `valueOf PUBLIC returns PUBLIC`() {
        assertEquals(Visibility.PUBLIC, Visibility.valueOf("PUBLIC"))
    }

    @Test
    fun `valueOf PROTECTED returns PROTECTED`() {
        assertEquals(Visibility.PROTECTED, Visibility.valueOf("PROTECTED"))
    }

    @Test
    fun `valueOf PRIVATE returns PRIVATE`() {
        assertEquals(Visibility.PRIVATE, Visibility.valueOf("PRIVATE"))
    }
}
