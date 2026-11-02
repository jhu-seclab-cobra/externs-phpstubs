package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * Original literal/gap name queries, without a regex language or graph state.
 * - `whole name boundaries and literal bytes are respected` — concrete text is never a regex.
 * - `empty and adjacent gaps preserve full middle constraints` — empty transitions and original literals.
 * - `one optional root separator and namespaces are matched` — canonical identity is not duplicated.
 * - `unresolved occurrences are independent while concrete replacements remain literal` — derived query contract.
 */
internal class NamePatternTest {
    private fun pattern(vararg parts: String?): NamePattern = NamePattern(parts.map { part ->
        if (part == null) NamePattern.Part.Gap else NamePattern.Part.Literal(part)
    })

    @Test
    fun `whole name boundaries and literal bytes are respected`() {
        assertTrue(pattern("str.len").matches("str.len"))
        assertFalse(pattern("str.len").matches("strlen"))
        assertFalse(pattern("str").matches("strlen"))
        assertFalse(pattern("str").matches("astr"))
        assertTrue(pattern("").matches(""))
        assertFalse(pattern("").matches("x"))
    }

    @Test
    fun `empty and adjacent gaps preserve full middle constraints`() {
        val original = pattern("a", null, null, "X", null, "b")
        assertTrue(original.matches("aXb"))
        assertTrue(original.matches("aaXXbb"))
        assertFalse(original.matches("ab"))
        assertFalse(original.matches("aX"))
        assertTrue(pattern(null, null).matches("anything"))
    }

    @Test
    fun `one optional root separator and namespaces are matched`() {
        assertTrue(pattern("\\n\\str", null).matches("n\\strlen"))
        assertTrue(pattern(null, "\\strlen").matches("strlen"))
        assertFalse(pattern("\\\\strlen").matches("strlen"))
        assertFalse(pattern("n/str", null).matches("n\\strlen"))
    }

    @Test
    fun `unresolved occurrences are independent while concrete replacements remain literal`() {
        val original = pattern("f", null, "X", null)
        assertEquals(listOf(true, true), listOf("faXa", "faXb").map(original::matches))
        assertEquals(listOf(true, false), listOf("faXa", "faXb").map(pattern("faXa")::matches))
    }
}
