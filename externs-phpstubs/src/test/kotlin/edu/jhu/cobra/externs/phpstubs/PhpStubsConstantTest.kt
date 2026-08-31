package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [PhpStubs] facade — global and class constant lookups.
 *
 * - `containsConst case-sensitive matches exact name` — verifies default lookup preserves constant case
 * - `containsConst returns true for class constant` — verifies class constant path in containsConst
 * - `containsConst case-insensitive matches any case` — verifies constCiIndex path
 * - `containsConst case-insensitive matches class constant` — verifies classConstCiIndex path
 * - `containsConst returns false for unknown constant` — verifies unknown constant returns false
 * - `searchGlobalConst returns Constant record` — verifies global constant retrieval
 * - `searchGlobalConst returns null for unknown` — verifies null return for missing constant
 * - `searchGlobalConst case-sensitive mismatch returns null` — verifies case mismatch fails by default
 * - `searchGlobalConst case-insensitive returns record` — verifies case-insensitive constant lookup
 * - `searchClassConst returns ClassConstant with className` — verifies class constant retrieval
 * - `searchClassConst returns null for unknown` — verifies null return for missing class constant
 * - `searchClassConst case-sensitive mismatch returns null` — verifies case mismatch fails by default
 * - `searchClassConst returns ClassConstant without className via suffix index` — verifies suffix-only class constant lookup
 * - `searchClassConst case-insensitive with className returns record` — verifies case-insensitive qualified class constant lookup
 * - `searchClassConst case-insensitive without className matches via suffix index` — verifies
 *   case-insensitive suffix lookup matches uppercase constants from lowercase input
 */
internal class PhpStubsConstantTest {
    @Test
    fun `containsConst case-sensitive matches exact name`() {
        assertTrue(PhpStubs.containsConst("TRUE"))
        assertFalse(PhpStubs.containsConst("true"))
    }

    @Test
    fun `containsConst returns true for class constant`() {
        assertTrue(PhpStubs.containsConst("exception::SEVERITY_ERROR"))
    }

    @Test
    fun `containsConst case-insensitive matches any case`() {
        assertTrue(PhpStubs.containsConst("true", caseSensitive = false))
        assertTrue(PhpStubs.containsConst("TRUE", caseSensitive = false))
    }

    @Test
    fun `containsConst case-insensitive matches class constant`() {
        assertTrue(PhpStubs.containsConst("exception::severity_error", caseSensitive = false))
    }

    @Test
    fun `containsConst returns false for unknown constant`() {
        assertFalse(PhpStubs.containsConst("nonexistent_xyz_const"))
    }

    @Test
    fun `searchGlobalConst returns Constant record`() {
        val record = PhpStubs.searchGlobalConst("TRUE")
        assertNotNull(record)
        assertIs<StubRecord.Constant>(record)
        assertEquals("TRUE", record.name)
    }

    @Test
    fun `searchGlobalConst returns null for unknown`() {
        assertNull(PhpStubs.searchGlobalConst("nonexistent_xyz_const"))
    }

    @Test
    fun `searchGlobalConst case-sensitive mismatch returns null`() {
        assertNull(PhpStubs.searchGlobalConst("php_int_max"))
    }

    @Test
    fun `searchGlobalConst case-insensitive returns record`() {
        val record = PhpStubs.searchGlobalConst("php_int_max", caseSensitive = false)
        assertNotNull(record)
        assertIs<StubRecord.Constant>(record)
        assertEquals("PHP_INT_MAX", record.name)
    }

    @Test
    fun `searchClassConst returns ClassConstant with className`() {
        val record = PhpStubs.searchClassConst("SEVERITY_ERROR", "Exception")
        assertNotNull(record)
        assertIs<StubRecord.ClassConstant>(record)
        assertEquals("SEVERITY_ERROR", record.name)
        assertEquals("Exception", record.owningClass)
    }

    @Test
    fun `searchClassConst returns null for unknown`() {
        assertNull(PhpStubs.searchClassConst("nonexistent_xyz_const", "exception"))
    }

    @Test
    fun `searchClassConst case-sensitive mismatch returns null`() {
        assertNull(PhpStubs.searchClassConst("severity_error", "Exception"))
    }

    @Test
    fun `searchClassConst returns ClassConstant without className via suffix index`() {
        val record = PhpStubs.searchClassConst("SEVERITY_ERROR")
        assertNotNull(record)
        assertIs<StubRecord.ClassConstant>(record)
        assertEquals("SEVERITY_ERROR", record.name)
        assertEquals("Exception", record.owningClass)
    }

    @Test
    fun `searchClassConst case-insensitive with className returns record`() {
        val record = PhpStubs.searchClassConst("severity_error", "Exception", caseSensitive = false)
        assertNotNull(record)
        assertIs<StubRecord.ClassConstant>(record)
        assertEquals("SEVERITY_ERROR", record.name)
    }

    @Test
    fun `searchClassConst case-insensitive without className matches via suffix index`() {
        val record = PhpStubs.searchClassConst("severity_error", caseSensitive = false)
        assertNotNull(record)
        assertIs<StubRecord.ClassConstant>(record)
        assertEquals("SEVERITY_ERROR", record.name)
        assertEquals("Exception", record.owningClass)
    }
}
