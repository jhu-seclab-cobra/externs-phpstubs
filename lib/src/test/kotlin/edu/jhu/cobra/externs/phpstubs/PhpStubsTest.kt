package edu.jhu.cobra.externs.phpstubs

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
    fun `searchFunc should return record for known function`() {
        val record = PhpStubs.searchFunc("strlen")
        assertNotNull(record)
        assertEquals("strlen", record.name)
        assertTrue(record.extension.isNotEmpty())
    }

    @Test
    fun `searchFunc should return keyword record for keyword function`() {
        val record = PhpStubs.searchFunc("echo")
        assertNotNull(record)
        assertEquals("keyword", record.extension)
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
    fun `searchClass should return scalar record`() {
        val record = PhpStubs.searchClass("int")
        assertNotNull(record)
        assertEquals("Scalar", record.extension)
    }

    @Test
    fun `containsMethod should find method with class name`() {
        // Most PHP classes have __construct
        assertTrue(PhpStubs.containsMethod("query", "mysqli"))
    }

    @Test
    fun `searchMethod should return pair with full name`() {
        val result = PhpStubs.searchMethod("query", "mysqli")
        assertNotNull(result)
        assertEquals("mysqli::query", result.first)
    }

    @Test
    fun `containsConst should return true for known constant`() {
        assertTrue(PhpStubs.containsConst("PHP_EOL") || PhpStubs.containsConst("php_eol"))
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

    @Test
    fun `getFuncRawData should return non-null bytes for known function`() {
        val bytes = PhpStubs.getFuncRawData("strlen")
        assertNotNull(bytes)
        assertTrue(bytes.isNotEmpty())
    }

    @Test
    fun `getFuncRawData should return null for unknown function`() {
        assertNull(PhpStubs.getFuncRawData("nonexistent_xyz_func"))
    }
}
