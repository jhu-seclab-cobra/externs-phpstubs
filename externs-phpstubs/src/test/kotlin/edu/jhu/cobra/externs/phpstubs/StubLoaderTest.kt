package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for [StubLoader] YAML-based loading.
 * Test data in `/stubs-test/` with `standard.yaml` and `core.yaml`.
 */
internal class StubLoaderTest {

    private val registry: StubRegistry by lazy { StubLoader.loadAll("/stubs-test/") }

    // -- Functions --

    @Test
    fun `loads functions from both YAML files`() {
        assertTrue(registry.functions.containsKey("strlen"))
        assertTrue(registry.functions.containsKey("substr"))
        assertTrue(registry.functions.containsKey("define"))
    }

    @Test
    fun `function records have correct extension`() {
        assertEquals("standard", registry.functions["strlen"]?.extension)
        assertEquals("core", registry.functions["define"]?.extension)
    }

    @Test
    fun `function records have parsed params`() {
        val substr = registry.functions["substr"]
        assertNotNull(substr)
        assertEquals(3, substr.params.size)
        assertEquals("string", substr.params[0].name)
        assertEquals(PhpType.STRING, substr.params[0].type)
    }

    @Test
    fun `function records have return type`() {
        assertEquals(PhpType.INT, registry.functions["strlen"]?.returnType)
        assertEquals(PhpType.STRING, registry.functions["substr"]?.returnType)
    }

    @Test
    fun `function records have flowsToReturn`() {
        assertEquals(setOf(0), registry.functions["substr"]?.flowsToReturn)
        assertEquals(setOf(0, 1, 2), registry.functions["str_replace"]?.flowsToReturn)
        assertEquals(emptySet(), registry.functions["strlen"]?.flowsToReturn)
    }

    // -- Classes --

    @Test
    fun `loads classes from YAML`() {
        assertTrue(registry.classes.containsKey("Exception"))
        val exception = registry.classes["Exception"]
        assertNotNull(exception)
        assertIs<StubRecord.PhpClass>(exception)
        assertEquals("core", exception.extension)
        assertEquals(listOf("Throwable"), exception.interfaces)
    }

    // -- Methods --

    @Test
    fun `loads methods with class double-colon name keys`() {
        assertTrue(registry.methods.containsKey("Exception::getMessage"))
        val m = registry.methods["Exception::getMessage"]
        assertNotNull(m)
        assertEquals("Exception", m.owningClass)
        assertEquals("getMessage", m.name)
        assertEquals(PhpType.STRING, m.returnType)
    }

    // -- Constants --

    @Test
    fun `loads constants with values`() {
        val phpEol = registry.constants["PHP_EOL"]
        assertNotNull(phpEol)
        assertEquals("\n", phpEol.value)

        val phpIntMax = registry.constants["PHP_INT_MAX"]
        assertNotNull(phpIntMax)
        assertEquals("9223372036854775807", phpIntMax.value)
        assertEquals(PhpType.INT, phpIntMax.type)
    }

    // -- Class constants --

    @Test
    fun `loads class constants with class double-colon name keys`() {
        val seekSet = registry.classConstants["SplFileObject::SEEK_SET"]
        assertNotNull(seekSet)
        assertEquals("0", seekSet.value)
        assertEquals("SplFileObject", seekSet.owningClass)
    }

    // -- Properties --

    @Test
    fun `loads properties with class double-colon name keys`() {
        val msg = registry.properties["Exception::message"]
        assertNotNull(msg)
        assertEquals(Visibility.PROTECTED, msg.visibility)
        assertEquals(PhpType.STRING, msg.type)
        assertEquals("Exception", msg.owningClass)
    }

    // -- Error handling --

    @Test
    fun `missing index file throws StubIndexNotFoundException`() {
        assertFailsWith<StubIndexNotFoundException> {
            StubLoader.loadAll("/nonexistent-path/")
        }
    }

    // -- Immutability --

    @Test
    fun `functions map is unmodifiable`() {
        assertFailsWith<UnsupportedOperationException> {
            @Suppress("UNCHECKED_CAST")
            (registry.functions as MutableMap<String, StubRecord.Function>)["hack"] =
                StubRecord.Function(name = "hack", extension = "test")
        }
    }
}
