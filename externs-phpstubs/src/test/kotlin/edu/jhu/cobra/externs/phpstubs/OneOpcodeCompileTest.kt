package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.SignatureInfo.CallableSignature
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for the facts php-src's call compiler fixes for a call to one opcode, read into the callable signature
 * (design-extraction-signatures.md, extract_signatures.py).
 *
 * - `a frameless function lists the counts the selection rule picks` — verifies strpos, str_replace, trim, min
 * - `a variadic function lists only the count equal to a tag arity` — verifies implode and max
 * - `an alias of a frameless function lists no count` — verifies join and strchr
 * - `array_key_exists lists its two operands as a special count` — verifies the function the stubs do not tag
 * - `a function compiled with fewer than two operands lists no count` — verifies strlen and count
 * - `sprintf names its format parameter` — verifies the rope fact and its absence on printf
 * - `the frameless set lists exactly the 19 php-src 8.5.11 functions` — verifies the closure over the set
 * - `the special set lists exactly array_key_exists` — verifies the closure over the set
 */
internal class OneOpcodeCompileTest {
    @Test
    fun `a frameless function lists the counts the selection rule picks`() {
        assertEquals(setOf(2, 3), signature("strpos").framelessArities)
        assertEquals(setOf(3), signature("str_replace").framelessArities)
        assertEquals(setOf(1, 2), signature("trim").framelessArities)
        assertEquals(setOf(2), signature("min").framelessArities)
    }

    @Test
    fun `a variadic function lists only the count equal to a tag arity`() {
        assertEquals(setOf(1, 2), signature("implode").framelessArities)
        assertEquals(setOf(2), signature("max").framelessArities)
    }

    @Test
    fun `an alias of a frameless function lists no count`() {
        assertTrue(signature("join").framelessArities.isEmpty())
        assertTrue(signature("strchr").framelessArities.isEmpty())
    }

    @Test
    fun `array_key_exists lists its two operands as a special count`() {
        assertEquals(setOf(2), signature("array_key_exists").specialArities)
        assertTrue(signature("array_key_exists").framelessArities.isEmpty())
    }

    @Test
    fun `a function compiled with fewer than two operands lists no count`() {
        for (name in listOf("strlen", "count")) {
            assertTrue(signature(name).framelessArities.isEmpty())
            assertTrue(signature(name).specialArities.isEmpty())
        }
    }

    @Test
    fun `sprintf names its format parameter`() {
        assertEquals("format", signature("sprintf").ropeFormat)
        assertNull(signature("printf").ropeFormat)
        assertNull(signature("vsprintf").ropeFormat)
    }

    @Test
    fun `the frameless set lists exactly the 19 php-src 8_5_11 functions`() {
        val expected =
            """
            property_exists min max str_contains str_starts_with preg_match class_exists trim implode dirname
            in_array strstr strpos substr strtr str_replace preg_replace dechex is_numeric
            """.trim().split(Regex("\\s+")).toSet()
        assertEquals(19, expected.size)
        assertEquals(expected, namesWith { it.framelessArities.isNotEmpty() })
    }

    @Test
    fun `the special set lists exactly array_key_exists`() {
        assertEquals(setOf("array_key_exists"), namesWith { it.specialArities.isNotEmpty() })
        assertEquals(setOf("sprintf"), namesWith { it.ropeFormat != null })
    }

    private fun namesWith(test: (CallableSignature) -> Boolean): Set<String> =
        PhpStubs.functions
            .filter { (it.callableSignature)?.let(test) == true }
            .map { it.subject.name }
            .toSet()

    private fun signature(name: String): CallableSignature = assertNotNull(PhpStubs.function(name)).callableSignature!!
}
