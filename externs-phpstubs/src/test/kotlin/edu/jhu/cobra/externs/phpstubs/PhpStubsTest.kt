package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [PhpStubs] facade.
 */
internal class PhpStubsTest {

    // -- Keywords --

    @Test
    fun `containsFunc returns true for keyword functions`() {
        assertTrue(PhpStubs.containsFunc("echo"))
        assertTrue(PhpStubs.containsFunc("isset"))
        assertTrue(PhpStubs.containsFunc("require"))
        assertTrue(PhpStubs.containsFunc("include_once"))
    }

    @Test
    fun `containsFunc returns false for unknown function`() {
        assertFalse(PhpStubs.containsFunc("nonexistent_xyz_func"))
    }

    @Test
    fun `searchFunc returns keyword Function record`() {
        val record = PhpStubs.searchFunc("echo")
        assertNotNull(record)
        assertIs<StubRecord.Function>(record)
        assertEquals("echo", record.name)
        assertEquals("keyword", record.extension)
    }

    @Test
    fun `searchFunc returns null for unknown function`() {
        assertNull(PhpStubs.searchFunc("nonexistent_xyz_func"))
    }

    // -- Scalar types --

    @Test
    fun `containsClass returns true for scalar types`() {
        assertTrue(PhpStubs.containsClass("int"))
        assertTrue(PhpStubs.containsClass("string"))
        assertTrue(PhpStubs.containsClass("array"))
    }

    @Test
    fun `searchClass returns PhpClass record`() {
        val record = PhpStubs.searchClass("int")
        assertNotNull(record)
        assertIs<StubRecord.PhpClass>(record)
        assertEquals("Scalar", record.extension)
    }

    @Test
    fun `containsClass returns true for exit and resource`() {
        assertTrue(PhpStubs.containsClass("exit"))
        assertTrue(PhpStubs.containsClass("resource"))
    }

    // -- Normalization --

    @Test
    fun `normalize strips forward slash and lowercases`() {
        with(PhpStubs) {
            assertEquals("strlen", "strlen".normalize())
            assertEquals("strlen", "/strlen".normalize())
            assertEquals("strlen", "Strlen".normalize())
            assertEquals("strlen", "/STRLEN".normalize())
        }
    }

    @Test
    fun `normalize strips backslash`() {
        with(PhpStubs) {
            assertEquals("strlen", "\\strlen".normalize())
            assertEquals("strlen", "\\STRLEN".normalize())
        }
    }

    // -- Bulk access --

    @Test
    fun `getKeywordFuncNames contains standard keywords`() {
        val keywords = PhpStubs.getKeywordFuncNames()
        assertTrue("echo" in keywords)
        assertTrue("isset" in keywords)
        assertTrue("require" in keywords)
    }

    @Test
    fun `getScalarTypeNames contains all scalar types`() {
        val scalars = PhpStubs.getScalarTypeNames()
        assertEquals(5, scalars.size)
        assertTrue("int" in scalars)
        assertTrue("string" in scalars)
    }
}
