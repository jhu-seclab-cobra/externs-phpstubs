package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [StubRecord] sealed class and its subtypes.
 *
 * Each subtype tested for: required fields, default values, data class equality/copy.
 */
internal class StubRecordTest {

    // -- Function --

    @Test
    fun `Function with minimal fields`() {
        val f = StubRecord.Function(name = "strlen", extension = "standard")
        assertEquals("strlen", f.name)
        assertEquals("standard", f.extension)
        assertTrue(f.params.isEmpty())
        assertEquals(PhpType.MIXED, f.returnType)
        assertTrue(f.flowsToReturn.isEmpty())
    }

    @Test
    fun `Function with all fields`() {
        val params = listOf(StubParam("s", PhpType.STRING))
        val f = StubRecord.Function(
            name = "substr",
            extension = "standard",
            params = params,
            returnType = PhpType.STRING,
            flowsToReturn = setOf(0),
        )
        assertEquals(params, f.params)
        assertEquals(PhpType.STRING, f.returnType)
        assertEquals(setOf(0), f.flowsToReturn)
    }

    @Test
    fun `Function is StubRecord`() {
        val f: StubRecord = StubRecord.Function(name = "strlen", extension = "standard")
        assertEquals("strlen", f.name)
    }

    // -- Method --

    @Test
    fun `Method with minimal fields`() {
        val m = StubRecord.Method(name = "query", extension = "pdo", owningClass = "PDO")
        assertEquals("query", m.name)
        assertEquals("PDO", m.owningClass)
        assertEquals(Visibility.PUBLIC, m.visibility)
        assertFalse(m.isStatic)
    }

    @Test
    fun `Method with all fields`() {
        val m = StubRecord.Method(
            name = "getInstance",
            extension = "core",
            owningClass = "Singleton",
            params = listOf(StubParam("x", PhpType.INT)),
            returnType = PhpType.OBJECT,
            flowsToReturn = setOf(0),
            visibility = Visibility.PRIVATE,
            isStatic = true,
        )
        assertTrue(m.isStatic)
        assertEquals(Visibility.PRIVATE, m.visibility)
        assertEquals(setOf(0), m.flowsToReturn)
    }

    // -- PhpClass --

    @Test
    fun `PhpClass with minimal fields`() {
        val c = StubRecord.PhpClass(name = "stdClass", extension = "core")
        assertNull(c.parent)
        assertTrue(c.interfaces.isEmpty())
        assertFalse(c.isAbstract)
        assertFalse(c.isFinal)
    }

    @Test
    fun `PhpClass with inheritance`() {
        val c = StubRecord.PhpClass(
            name = "RuntimeException",
            extension = "core",
            parent = "Exception",
            interfaces = listOf("Throwable"),
            isAbstract = false,
            isFinal = true,
        )
        assertEquals("Exception", c.parent)
        assertEquals(listOf("Throwable"), c.interfaces)
        assertTrue(c.isFinal)
    }

    // -- Constant --

    @Test
    fun `Constant requires type and value`() {
        val c = StubRecord.Constant(
            name = "PHP_INT_MAX",
            extension = "core",
            type = PhpType.INT,
            value = "9223372036854775807",
        )
        assertEquals(PhpType.INT, c.type)
        assertEquals("9223372036854775807", c.value)
    }

    // -- ClassConstant --

    @Test
    fun `ClassConstant with owningClass`() {
        val cc = StubRecord.ClassConstant(
            name = "SEEK_SET",
            extension = "spl",
            owningClass = "SplFileObject",
            type = PhpType.INT,
            value = "0",
        )
        assertEquals("SplFileObject", cc.owningClass)
        assertEquals(Visibility.PUBLIC, cc.visibility)
    }

    // -- Property --

    @Test
    fun `Property with minimal fields`() {
        val p = StubRecord.Property(
            name = "message",
            extension = "core",
            owningClass = "Exception",
        )
        assertEquals(PhpType.MIXED, p.type)
        assertEquals(Visibility.PUBLIC, p.visibility)
        assertFalse(p.isStatic)
    }

    @Test
    fun `Property with all fields`() {
        val p = StubRecord.Property(
            name = "instance",
            extension = "core",
            owningClass = "Singleton",
            type = PhpType.OBJECT,
            visibility = Visibility.PRIVATE,
            isStatic = true,
        )
        assertTrue(p.isStatic)
        assertEquals(Visibility.PRIVATE, p.visibility)
        assertEquals(PhpType.OBJECT, p.type)
    }

    // -- Data class equality --

    @Test
    fun `equal Functions are equal`() {
        val a = StubRecord.Function(name = "strlen", extension = "standard", returnType = PhpType.INT)
        val b = StubRecord.Function(name = "strlen", extension = "standard", returnType = PhpType.INT)
        assertEquals(a, b)
    }

    @Test
    fun `Function copy preserves fields`() {
        val original = StubRecord.Function(name = "strlen", extension = "standard")
        val copied = original.copy(returnType = PhpType.INT)
        assertEquals(PhpType.INT, copied.returnType)
        assertEquals("strlen", copied.name)
    }
}
