package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * Tests for [StubRegistry] data class.
 */
internal class StubRegistryTest {

    @Test
    fun `construction with empty maps`() {
        val registry = StubRegistry(
            functions = emptyMap(),
            classes = emptyMap(),
            methods = emptyMap(),
            constants = emptyMap(),
            classConstants = emptyMap(),
            properties = emptyMap(),
        )
        assertTrue(registry.functions.isEmpty())
        assertTrue(registry.classes.isEmpty())
        assertTrue(registry.methods.isEmpty())
        assertTrue(registry.constants.isEmpty())
        assertTrue(registry.classConstants.isEmpty())
        assertTrue(registry.properties.isEmpty())
    }

    @Test
    fun `construction with populated maps`() {
        val f = StubRecord.Function(name = "strlen", extension = "standard")
        val c = StubRecord.PhpClass(name = "Exception", extension = "core")
        val m = StubRecord.Method(name = "getMessage", extension = "core", owningClass = "Exception")
        val k = StubRecord.Constant(name = "PHP_EOL", extension = "core", type = PhpType.STRING, value = "\n")
        val cc = StubRecord.ClassConstant(name = "SEEK_SET", extension = "spl", owningClass = "SplFileObject", type = PhpType.INT, value = "0")
        val p = StubRecord.Property(name = "message", extension = "core", owningClass = "Exception")

        val registry = StubRegistry(
            functions = mapOf("strlen" to f),
            classes = mapOf("Exception" to c),
            methods = mapOf("Exception::getMessage" to m),
            constants = mapOf("PHP_EOL" to k),
            classConstants = mapOf("SplFileObject::SEEK_SET" to cc),
            properties = mapOf("Exception::message" to p),
        )
        assertEquals(f, registry.functions["strlen"])
        assertEquals(c, registry.classes["Exception"])
        assertEquals(m, registry.methods["Exception::getMessage"])
        assertEquals(k, registry.constants["PHP_EOL"])
        assertEquals(cc, registry.classConstants["SplFileObject::SEEK_SET"])
        assertEquals(p, registry.properties["Exception::message"])
    }
}
