package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.value.ListVal
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class PhpStubsTest {

    @Test
    fun `containsFunc should return true for known builtin function`() {
        assertTrue(PhpStubs.containsFunc("strlen"))
        assertTrue(PhpStubs.containsFunc("substr"))
        assertTrue(PhpStubs.containsFunc("array_map"))
    }

    @Test
    fun `containsFunc should normalize leading slash and case`() {
        assertTrue(PhpStubs.containsFunc("/strlen"))
        assertTrue(PhpStubs.containsFunc("Strlen"))
        assertTrue(PhpStubs.containsFunc("/STRLEN"))
    }

    @Test
    fun `containsFunc should return true for keyword functions`() {
        assertTrue(PhpStubs.containsFunc("echo"))
        assertTrue(PhpStubs.containsFunc("isset"))
        assertTrue(PhpStubs.containsFunc("require"))
        assertTrue(PhpStubs.containsFunc("include_once"))
    }

    @Test
    fun `containsFunc should return false for unknown function`() {
        assertFalse(PhpStubs.containsFunc("nonexistent_xyz_func"))
    }

    @Test
    fun `searchFunc should return record with IValue for known function`() {
        val record = PhpStubs.searchFunc("strlen")
        assertNotNull(record)
        assertEquals("strlen", record.name)
        assertTrue(record.extension.isNotEmpty())
        assertNotNull(record.value)
    }

    @Test
    fun `searchFunc should return keyword record with ListVal`() {
        val record = PhpStubs.searchFunc("echo")
        assertNotNull(record)
        assertEquals("keyword", record.extension)
        assertTrue(record.value is ListVal)
    }

    @Test
    fun `searchFunc should return null for unknown function`() {
        assertNull(PhpStubs.searchFunc("nonexistent_xyz_func"))
    }

    @Test
    fun `containsClass should return true for known class`() {
        assertTrue(PhpStubs.containsClass("exception"))
        assertTrue(PhpStubs.containsClass("stdclass"))
    }

    @Test
    fun `containsClass should return true for scalar types`() {
        assertTrue(PhpStubs.containsClass("int"))
        assertTrue(PhpStubs.containsClass("string"))
        assertTrue(PhpStubs.containsClass("array"))
    }

    @Test
    fun `searchClass should return scalar record with IValue`() {
        val record = PhpStubs.searchClass("int")
        assertNotNull(record)
        assertEquals("Scalar", record.extension)
        assertTrue(record.value is ListVal)
    }

    @Test
    fun `containsMethod should find method with class name`() {
        assertTrue(PhpStubs.containsMethod("query", "mysqli"))
    }

    @Test
    fun `searchMethod should return pair with full name and IValue`() {
        val result = PhpStubs.searchMethod("query", "mysqli")
        assertNotNull(result)
        assertEquals("mysqli::query", result.first)
        assertNotNull(result.second.value)
    }

    @Test
    fun `containsConst should return true for known constant`() {
        assertTrue(PhpStubs.containsConst("PHP_EOL") || PhpStubs.containsConst("php_eol"))
    }

    @Test
    fun `searchGlobalConst should return record with IValue`() {
        val record = PhpStubs.searchGlobalConst("php_eol")
        assertNotNull(record)
        assertNotNull(record.value)
    }

    @Test
    fun `getAllFuncNames should return non-empty set`() {
        val names = PhpStubs.getAllFuncNames()
        assertTrue(names.size > 1000, "Expected > 1000 functions, got ${names.size}")
    }

    @Test
    fun `getAllClassNames should return non-empty set`() {
        val names = PhpStubs.getAllClassNames()
        assertTrue(names.size > 100, "Expected > 100 classes, got ${names.size}")
    }

    @Test
    fun `getAllMethodNames should return non-empty set`() {
        val names = PhpStubs.getAllMethodNames()
        assertTrue(names.size > 1000, "Expected > 1000 methods, got ${names.size}")
    }

    @Test
    fun `getAllConstNames should return non-empty set`() {
        val names = PhpStubs.getAllConstNames()
        assertTrue(names.size > 1000, "Expected > 1000 constants, got ${names.size}")
    }

    @Test
    fun `getKeywordFuncNames should contain standard keywords`() {
        val keywords = PhpStubs.getKeywordFuncNames()
        assertTrue("echo" in keywords)
        assertTrue("isset" in keywords)
        assertTrue("require" in keywords)
    }
}
