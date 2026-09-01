package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull

/**
 * Tests for [StubRegistry] as an immutable per-kind map holder.
 *
 * - `registry holds one map per subject kind` — verifies every kind of the fixture lands in its own map
 * - `registries with equal maps are equal` — verifies data class equality over the maps
 * - `functions map is unmodifiable` — verifies the frozen map rejects writes
 */
internal class StubRegistryTest {
    private val registry: StubRegistry by lazy { StubLoader.loadAll("/models-test/") }

    @Test
    fun `registry holds one map per subject kind`() {
        assertEquals(
            listOf(5, 5, 3, 3, 2, 1),
            listOf(
                registry.functions.size,
                registry.classes.size,
                registry.methods.size,
                registry.constants.size,
                registry.classConstants.size,
                registry.properties.size,
            ),
        )
    }

    @Test
    fun `registries with equal maps are equal`() {
        val copy =
            StubRegistry(
                functions = registry.functions,
                classes = registry.classes,
                methods = registry.methods,
                constants = registry.constants,
                classConstants = registry.classConstants,
                properties = registry.properties,
            )
        assertEquals(registry, copy)
    }

    @Test
    fun `functions map is unmodifiable`() {
        val entry = assertNotNull(registry.functions[FunctionSubject("strlen")])
        assertFailsWith<UnsupportedOperationException> {
            @Suppress("UNCHECKED_CAST")
            (registry.functions as MutableMap<FunctionSubject, StubEntry<FunctionSubject>>)[FunctionSubject("hack")] = entry
        }
    }
}
