package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * Tests for the shared stub key normalization in StubKey.kt, used by both
 * [StubLoader] key construction and [PhpStubs] lookup queries.
 *
 * - `normalizeStubKey strips forward slash and lowercases` -- verifies leading `/` removal and lowercasing
 * - `normalizeStubKey strips backslash` -- verifies leading `\` removal and lowercasing
 * - `normalizeStubKey strips only one leading separator` -- verifies a single separator is removed
 * - `stripLeadingSlash preserves case` -- verifies case-sensitive stripping for constants
 */
internal class StubKeyTest {
    @Test
    fun `normalizeStubKey strips forward slash and lowercases`() {
        assertEquals("strlen", "strlen".normalizeStubKey())
        assertEquals("strlen", "/strlen".normalizeStubKey())
        assertEquals("strlen", "Strlen".normalizeStubKey())
        assertEquals("strlen", "/STRLEN".normalizeStubKey())
    }

    @Test
    fun `normalizeStubKey strips backslash`() {
        assertEquals("strlen", "\\strlen".normalizeStubKey())
        assertEquals("strlen", "\\STRLEN".normalizeStubKey())
    }

    @Test
    fun `normalizeStubKey strips only one leading separator`() {
        assertEquals("/strlen", "//strlen".normalizeStubKey())
        assertEquals("\\strlen", "\\\\strlen".normalizeStubKey())
    }

    @Test
    fun `stripLeadingSlash preserves case`() {
        assertEquals("PHP_EOL", "/PHP_EOL".stripLeadingSlash())
        assertEquals("PHP_EOL", "\\PHP_EOL".stripLeadingSlash())
        assertEquals("PHP_EOL", "PHP_EOL".stripLeadingSlash())
    }
}
