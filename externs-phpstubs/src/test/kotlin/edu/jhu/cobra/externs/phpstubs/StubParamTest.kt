package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [StubParam] data class.
 *
 * - `construction with all fields` -- explicit values round-trip.
 * - `default optional is false` -- optional defaults to false.
 * - `default defaultValue is null` -- defaultValue defaults to null.
 * - `non-optional param with defaultValue throws IllegalArgumentException` -- validation.
 * - `optional param with defaultValue succeeds` -- valid combination.
 * - `optional param without defaultValue succeeds` -- optional alone is valid.
 * - `empty name string accepted` -- no name validation in StubParam.
 * - `data class equality for identical params` -- equals contract.
 * - `data class inequality for different names` -- equals contract.
 * - `copy preserves fields` -- data class copy.
 */
internal class StubParamTest {
    @Test
    fun `construction with all fields`() {
        val param =
            StubParam(
                name = "offset",
                type = PhpType.INT,
                optional = true,
                defaultValue = "0",
            )
        assertEquals("offset", param.name)
        assertEquals(PhpType.INT, param.type)
        assertTrue(param.optional)
        assertEquals("0", param.defaultValue)
    }

    @Test
    fun `default optional is false`() {
        val param = StubParam(name = "x", type = PhpType.STRING)
        assertFalse(param.optional)
    }

    @Test
    fun `default defaultValue is null`() {
        val param = StubParam(name = "x", type = PhpType.STRING)
        assertNull(param.defaultValue)
    }

    @Test
    fun `non-optional param with defaultValue throws IllegalArgumentException`() {
        assertFailsWith<IllegalArgumentException> {
            StubParam(name = "x", type = PhpType.STRING, optional = false, defaultValue = "hello")
        }
    }

    @Test
    fun `optional param with defaultValue succeeds`() {
        val param = StubParam(name = "x", type = PhpType.INT, optional = true, defaultValue = "10")
        assertTrue(param.optional)
        assertEquals("10", param.defaultValue)
    }

    @Test
    fun `optional param without defaultValue succeeds`() {
        val param = StubParam(name = "x", type = PhpType.INT, optional = true)
        assertTrue(param.optional)
        assertNull(param.defaultValue)
    }

    @Test
    fun `empty name string accepted`() {
        val param = StubParam(name = "", type = PhpType.MIXED)
        assertEquals("", param.name)
    }

    @Test
    fun `data class equality for identical params`() {
        val a = StubParam(name = "x", type = PhpType.STRING)
        val b = StubParam(name = "x", type = PhpType.STRING)
        assertEquals(a, b)
    }

    @Test
    fun `data class inequality for different names`() {
        val a = StubParam(name = "x", type = PhpType.STRING)
        val b = StubParam(name = "y", type = PhpType.STRING)
        assertNotEquals(a, b)
    }

    @Test
    fun `copy preserves fields`() {
        val original = StubParam(name = "len", type = PhpType.INT, optional = true, defaultValue = "0")
        val copy = original.copy()
        assertEquals(original, copy)
    }
}
