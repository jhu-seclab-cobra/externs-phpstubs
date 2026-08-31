package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [PhpStubs] facade — function, class, and method lookups plus bulk access.
 * Constant lookups: [PhpStubsConstantTest].
 *
 * - `containsFunc returns true for keyword functions` — verifies keyword lookups succeed
 * - `containsFunc returns false for unknown function` — verifies unknown names return false
 * - `containsFunc returns true for registry-loaded function` — verifies registry function lookup
 * - `searchFunc returns keyword Function record` — verifies record fields for a keyword function
 * - `searchFunc returns null for unknown function` — verifies null return for missing names
 * - `searchFunc returns registry Function record` — verifies record fields for a registry function
 * - `searchFunc normalizes case and leading slash` — verifies facade input normalization
 * - `containsClass returns true for scalar types` — verifies scalar type lookups succeed
 * - `containsClass returns false for unknown class` — verifies unknown class returns false
 * - `containsClass returns true for registry-loaded class` — verifies registry class lookup
 * - `searchClass returns PhpClass record` — verifies record fields for a scalar type
 * - `searchClass returns registry PhpClass record` — verifies record fields for a registry class
 * - `searchClass returns null for unknown class` — verifies null return for missing class
 * - `searchClass normalizes case and leading backslash` — verifies facade input normalization
 * - `containsClass returns true for exit and resource` — verifies special built-in types
 * - `containsMethod returns true with className for known method` — verifies qualified method lookup
 * - `containsMethod returns false for unknown method` — verifies unknown method returns false
 * - `containsMethod returns true without className via suffix index` — verifies suffix-only method lookup
 * - `searchMethod returns pair for known method with className` — verifies qualified method retrieval
 * - `searchMethod returns null for unknown method` — verifies null return for missing method
 * - `searchMethod returns pair without className via suffix index` — verifies suffix-only method retrieval
 * - `getKeywordFuncNames contains standard keywords` — verifies bulk keyword name retrieval
 * - `getScalarTypeNames contains all scalar types` — verifies bulk scalar type name retrieval
 * - `getAllFuncNames returns non-empty set` — verifies registry function names are populated
 * - `getAllClassNames returns non-empty set` — verifies registry class names are populated
 * - `getAllMethodNames returns non-empty set` — verifies registry method names are populated
 * - `getAllConstNames returns non-empty set` — verifies registry constant names are populated
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
    fun `containsFunc returns true for registry-loaded function`() {
        assertTrue(PhpStubs.containsFunc("strlen"))
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

    @Test
    fun `searchFunc returns registry Function record`() {
        val record = PhpStubs.searchFunc("strlen")
        assertNotNull(record)
        assertIs<StubRecord.Function>(record)
        assertEquals("strlen", record.name)
    }

    @Test
    fun `searchFunc normalizes case and leading slash`() {
        assertNotNull(PhpStubs.searchFunc("STRLEN"))
        assertNotNull(PhpStubs.searchFunc("/strlen"))
        assertNotNull(PhpStubs.searchFunc("\\Strlen"))
    }

    // -- Scalar types --

    @Test
    fun `containsClass returns true for scalar types`() {
        assertTrue(PhpStubs.containsClass("int"))
        assertTrue(PhpStubs.containsClass("string"))
        assertTrue(PhpStubs.containsClass("array"))
    }

    @Test
    fun `containsClass returns false for unknown class`() {
        assertFalse(PhpStubs.containsClass("nonexistent_xyz_class"))
    }

    @Test
    fun `containsClass returns true for registry-loaded class`() {
        assertTrue(PhpStubs.containsClass("exception"))
    }

    @Test
    fun `searchClass returns PhpClass record`() {
        val record = PhpStubs.searchClass("int")
        assertNotNull(record)
        assertIs<StubRecord.PhpClass>(record)
        assertEquals("Scalar", record.extension)
    }

    @Test
    fun `searchClass returns registry PhpClass record`() {
        val record = PhpStubs.searchClass("exception")
        assertNotNull(record)
        assertIs<StubRecord.PhpClass>(record)
        assertEquals("exception", record.name)
        assertEquals("core", record.extension)
    }

    @Test
    fun `searchClass returns null for unknown class`() {
        assertNull(PhpStubs.searchClass("nonexistent_xyz_class"))
    }

    @Test
    fun `searchClass normalizes case and leading backslash`() {
        assertNotNull(PhpStubs.searchClass("EXCEPTION"))
        assertNotNull(PhpStubs.searchClass("\\Exception"))
    }

    @Test
    fun `containsClass returns true for exit and resource`() {
        assertTrue(PhpStubs.containsClass("exit"))
        assertTrue(PhpStubs.containsClass("resource"))
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

    // -- Methods --

    @Test
    fun `containsMethod returns true with className for known method`() {
        assertTrue(PhpStubs.containsMethod("getmessage", "exception"))
    }

    @Test
    fun `containsMethod returns false for unknown method`() {
        assertFalse(PhpStubs.containsMethod("nonexistent_xyz_method", "exception"))
    }

    @Test
    fun `containsMethod returns true without className via suffix index`() {
        assertTrue(PhpStubs.containsMethod("getMessage"))
    }

    // -- Record retrieval (registry) --

    @Test
    fun `searchMethod returns pair for known method with className`() {
        val result = PhpStubs.searchMethod("getMessage", "Exception")
        assertNotNull(result)
        assertEquals("exception::getmessage", result.first)
        assertIs<StubRecord.Method>(result.second)
        assertEquals("getMessage", result.second.name)
    }

    @Test
    fun `searchMethod returns null for unknown method`() {
        assertNull(PhpStubs.searchMethod("nonexistent_xyz_method", "exception"))
    }

    @Test
    fun `searchMethod returns pair without className via suffix index`() {
        val result = PhpStubs.searchMethod("getMessage")
        assertNotNull(result)
        assertEquals("exception::getmessage", result.first)
        assertIs<StubRecord.Method>(result.second)
        assertEquals("getMessage", result.second.name)
    }

    // -- Bulk access (registry) --

    @Test
    fun `getAllFuncNames returns non-empty set`() {
        val names = PhpStubs.getAllFuncNames()
        assertTrue(names.isNotEmpty())
        assertTrue("strlen" in names)
    }

    @Test
    fun `getAllClassNames returns non-empty set`() {
        val names = PhpStubs.getAllClassNames()
        assertTrue(names.isNotEmpty())
        assertTrue("exception" in names)
    }

    @Test
    fun `getAllMethodNames returns non-empty set`() {
        val names = PhpStubs.getAllMethodNames()
        assertTrue(names.isNotEmpty())
        assertTrue("exception::getmessage" in names)
    }

    @Test
    fun `getAllConstNames returns non-empty set`() {
        val names = PhpStubs.getAllConstNames()
        assertTrue(names.isNotEmpty())
        assertTrue("TRUE" in names)
    }
}
