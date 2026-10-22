package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for the argument counts php-src compiles to one opcode, read into the callable signature
 * (design-extraction.md, extract_signatures.py).
 *
 * - `a frameless function lists the counts of its frameless variants` — verifies strpos, str_replace and trim
 * - `array_key_exists lists its two operands from the compiler dispatch` — verifies the function the stubs do not tag
 * - `a function compiled with fewer than two operands lists no count` — verifies strlen and count
 * - `the set lists exactly the php-src 8.5.11 functions` — verifies the closure over the set
 */
internal class OpcodeAritiesTest {
    @Test
    fun `a frameless function lists the counts of its frameless variants`() {
        assertEquals(setOf(2, 3), arities("strpos"))
        assertEquals(setOf(3), arities("str_replace"))
        assertEquals(setOf(1, 2), arities("trim"))
    }

    @Test
    fun `array_key_exists lists its two operands from the compiler dispatch`() {
        assertEquals(setOf(2), arities("array_key_exists"))
    }

    @Test
    fun `a function compiled with fewer than two operands lists no count`() {
        assertTrue(arities("strlen").isEmpty())
        assertTrue(arities("count").isEmpty())
    }

    @Test
    fun `the set lists exactly the php-src 8_5_11 functions`() {
        val listed = PhpStubs.functions.filter { it.callableSignature?.opcodeArities?.isNotEmpty() == true }
        val expected =
            """
            array_key_exists class_exists dechex dirname implode in_array is_numeric max min preg_match preg_replace
            property_exists str_contains str_replace str_starts_with strpos strstr strtr substr trim
            """.trim().split(Regex("\\s+")).toSet()
        assertEquals(
            expected,
            listed.map { it.subject.name }.toSet(),
        )
    }

    private fun arities(name: String): Set<Int> = assertNotNull(PhpStubs.function(name)).callableSignature!!.opcodeArities
}
