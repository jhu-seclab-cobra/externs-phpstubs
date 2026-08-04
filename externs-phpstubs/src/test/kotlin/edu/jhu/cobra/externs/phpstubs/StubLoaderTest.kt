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
 *
 * - `loads functions from both YAML files` — verifies functions from multiple YAML files are present
 * - `function records have correct extension` — verifies extension field matches source file
 * - `function records have parsed params` — verifies parameter list parsing
 * - `function records have return type` — verifies return type mapping
 * - `function records have flowsToReturn` — verifies taint flow index sets
 * - `loads classes from YAML` — verifies class record fields and interfaces
 * - `loads methods with class double-colon name keys` — verifies method keying and fields
 * - `loads constants with values` — verifies constant type and value parsing
 * - `constant key strips leading namespace slash` — verifies stored key matches slash-stripped queries
 * - `loads class constants with class double-colon name keys` — verifies class constant keying
 * - `loads properties with class double-colon name keys` — verifies property visibility and type
 * - `missing index file throws StubIndexNotFoundException` — verifies error on missing resource
 * - `missing stub file error names the stub file` — verifies the message reports the missing YAML path, not the index
 * - `invalid stub file error names the source file` — verifies parse errors carry the failing YAML path
 * - `duplicate key across files throws naming key and both files` — verifies merge rejects colliding normalized keys
 * - `functions map is unmodifiable` — verifies returned maps are immutable
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
        assertTrue(registry.classes.containsKey("exception"))
        val exception = registry.classes["exception"]
        assertNotNull(exception)
        assertIs<StubRecord.PhpClass>(exception)
        assertEquals("core", exception.extension)
        assertEquals(listOf("Throwable"), exception.interfaces)
    }

    // -- Methods --

    @Test
    fun `loads methods with class double-colon name keys`() {
        assertTrue(registry.methods.containsKey("exception::getmessage"))
        val m = registry.methods["exception::getmessage"]
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

    @Test
    fun `constant key strips leading namespace slash`() {
        val slashed = registry.constants["SLASHED_CONST"]
        assertNotNull(slashed)
        assertEquals("7", slashed.value)
    }

    // -- Class constants --

    @Test
    fun `loads class constants with class double-colon name keys`() {
        val seekSet = registry.classConstants["splfileobject::SEEK_SET"]
        assertNotNull(seekSet)
        assertEquals("0", seekSet.value)
        assertEquals("SplFileObject", seekSet.owningClass)
    }

    // -- Properties --

    @Test
    fun `loads properties with class double-colon name keys`() {
        val msg = registry.properties["exception::message"]
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

    @Test
    fun `missing stub file error names the stub file`() {
        val ex =
            assertFailsWith<StubIndexNotFoundException> {
                StubLoader.loadAll("/stubs-missing-file/")
            }
        assertEquals("Stub resource not found: /stubs-missing-file/ghost.yaml", ex.message)
    }

    @Test
    fun `invalid stub file error names the source file`() {
        val ex =
            assertFailsWith<StubIndexInvalidException> {
                StubLoader.loadAll("/stubs-invalid/")
            }
        val message = assertNotNull(ex.message)
        assertTrue(
            "/stubs-invalid/bad.yaml" in message,
            "expected message to name /stubs-invalid/bad.yaml, was: $message",
        )
    }

    @Test
    fun `duplicate key across files throws naming key and both files`() {
        val ex =
            assertFailsWith<StubIndexInvalidException> {
                StubLoader.loadAll("/stubs-duplicate/")
            }
        val message = assertNotNull(ex.message)
        assertTrue("'strlen'" in message, "expected message to name key 'strlen', was: $message")
        assertTrue("/stubs-duplicate/first.yaml" in message, "expected message to name first.yaml, was: $message")
        assertTrue("/stubs-duplicate/second.yaml" in message, "expected message to name second.yaml, was: $message")
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
