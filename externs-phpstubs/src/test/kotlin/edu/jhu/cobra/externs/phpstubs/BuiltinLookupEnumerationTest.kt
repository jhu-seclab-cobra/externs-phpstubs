package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.OriginId
import edu.jhu.cobra.commons.phpmodels.VulnClassId
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for the enumeration half of [BuiltinLookup], read through the bundled [PhpStubs] companion:
 * every record of one declaration kind, every fact of one fact kind, and the accumulated vocabulary and policy.
 * Exact lookups: [BuiltinLookupExactTest].
 *
 * - `enumerations cover every kind in first-statement order` — verifies the collections and fact lists
 * - `constant enumerations are non-empty and keyed by subject` — verifies bulk access
 * - `every enumerated record is reachable by exact lookup of its subject` — verifies the kind maps and the shared map agree
 * - `every enumerated fact belongs to the record that owns it` — verifies fact lists are built over the records
 * - `no psalm name survives the merge` — verifies the accumulated vocabulary holds only canonical names
 * - `the policy makes every category dangerous under both colors` — verifies the accumulated matrix
 */
internal class BuiltinLookupEnumerationTest {
    @Test
    fun `enumerations cover every kind in first-statement order`() {
        assertTrue(PhpStubs.functions.size > 5000)
        assertTrue(PhpStubs.classes.isNotEmpty() && PhpStubs.methods.isNotEmpty() && PhpStubs.constants.isNotEmpty())
        assertTrue(PhpStubs.classConstants.isNotEmpty() && PhpStubs.variables.isNotEmpty())
        assertTrue(PhpStubs.sinks.isNotEmpty() && PhpStubs.sources.isNotEmpty() && PhpStubs.sanitizers.isNotEmpty())
        assertTrue(PhpStubs.flows.isNotEmpty() && PhpStubs.returns.isNotEmpty())
        val first = PhpStubs.functions.first()
        assertEquals(first, PhpStubs.function(first.subject.name))
    }

    @Test
    fun `constant enumerations are non-empty and keyed by subject`() {
        assertTrue(PhpStubs.constants.size > 200)
        assertTrue(PhpStubs.classConstants.all { it.signature != null })
        assertTrue(PhpStubs.constants.all { PhpStubs.record(it.subject) === it })
    }

    @Test
    fun `every enumerated record is reachable by exact lookup of its subject`() {
        val kinds =
            listOf(
                PhpStubs.functions,
                PhpStubs.classes,
                PhpStubs.methods,
                PhpStubs.constants,
                PhpStubs.classConstants,
                PhpStubs.properties,
                PhpStubs.variables,
            )
        for (kind in kinds) {
            assertEquals(kind.size, kind.map { it.subject }.toSet().size)
            assertTrue(kind.all { PhpStubs.record(it.subject) === it })
        }
        val subjects = kinds.flatMap { kind -> kind.map { it.subject } }
        assertEquals(subjects.size, subjects.toSet().size)
    }

    @Test
    fun `every enumerated fact belongs to the record that owns it`() {
        assertTrue(PhpStubs.sinks.all { it in assertNotNull(PhpStubs.record(it.owner)).sinks })
        assertTrue(PhpStubs.sources.all { it in assertNotNull(PhpStubs.record(it.owner)).sources })
        assertTrue(PhpStubs.sanitizers.all { it in assertNotNull(PhpStubs.record(it.owner)).sanitizers })
        assertTrue(PhpStubs.flows.all { it in assertNotNull(PhpStubs.record(it.owner)).flows })
        assertTrue(PhpStubs.returns.all { it in assertNotNull(PhpStubs.record(it.owner)).returns })
    }

    @Test
    fun `no psalm name survives the merge`() {
        assertEquals(VulnClass.entries.map { it.id }.toSet(), PhpStubs.vocabulary.vulnClasses.keys)
        assertEquals(Origin.entries.map { it.id }.toSet(), PhpStubs.vocabulary.origins.keys)
        assertTrue(PhpStubs.sinks.none { it.vulnClass.id in setOf("sql", "html", "shell") })
    }

    @Test
    fun `the policy makes every category dangerous under both colors`() {
        for (origin in Origin.entries) {
            for (category in VulnClass.entries) {
                assertTrue(PhpStubs.policy.isDangerous(origin.id, category.id), "${origin.id.id} -> ${category.id.id}")
            }
        }
        assertTrue(PhpStubs.policy.isDangerous(OriginId("user-input"), VulnClassId("xpathi")))
    }
}
