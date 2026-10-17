package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.SourceKindId
import edu.jhu.cobra.commons.phpmodels.VulnTypeId
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
 * - `the policy makes every vulnerability type dangerous under both source kinds` — verifies the accumulated matrix
 */
internal class BuiltinLookupEnumerationTest {
    @Test
    fun `enumerations cover every kind in first-statement order`() {
        assertTrue(PhpStubs.functions.size > 5000)
        assertTrue(PhpStubs.classes.isNotEmpty() && PhpStubs.methods.isNotEmpty() && PhpStubs.constants.isNotEmpty())
        assertTrue(PhpStubs.classConstants.isNotEmpty() && PhpStubs.variables.isNotEmpty())
        assertTrue(PhpStubs.sinkFacts.isNotEmpty() && PhpStubs.sourceFacts.isNotEmpty() && PhpStubs.sanitizerFacts.isNotEmpty())
        assertTrue(PhpStubs.flows.isNotEmpty() && PhpStubs.returns.isNotEmpty() && PhpStubs.characters.isNotEmpty())
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
        assertTrue(PhpStubs.sinkFacts.all { it in assertNotNull(PhpStubs.record(it.owner)).sinkFacts })
        assertTrue(PhpStubs.sourceFacts.all { it in assertNotNull(PhpStubs.record(it.owner)).sourceFacts })
        assertTrue(PhpStubs.sanitizerFacts.all { it in assertNotNull(PhpStubs.record(it.owner)).sanitizerFacts })
        assertTrue(PhpStubs.flows.all { it in assertNotNull(PhpStubs.record(it.owner)).flows })
        assertTrue(PhpStubs.returns.all { it in assertNotNull(PhpStubs.record(it.owner)).returns })
        assertTrue(PhpStubs.characters.all { it in assertNotNull(PhpStubs.record(it.owner)).characters })
    }

    @Test
    fun `no psalm name survives the merge`() {
        assertEquals(VulnType.entries.map { it.id }.toSet(), PhpStubs.vocabulary.vulnTypes.keys)
        assertEquals(SourceKind.entries.map { it.id }.toSet(), PhpStubs.vocabulary.sourceKinds.keys)
        assertTrue(PhpStubs.sinkFacts.none { it.vulnType.id in setOf("sql", "html", "shell") })
    }

    @Test
    fun `the policy makes every vulnerability type dangerous under both source kinds`() {
        for (sourceKind in SourceKind.entries) {
            for (vulnType in VulnType.entries) {
                assertTrue(PhpStubs.policy.isDangerous(sourceKind.id, vulnType.id), "${sourceKind.id.id} -> ${vulnType.id.id}")
            }
        }
        assertTrue(PhpStubs.policy.isDangerous(SourceKindId("user-input"), VulnTypeId("xpathi")))
    }
}
