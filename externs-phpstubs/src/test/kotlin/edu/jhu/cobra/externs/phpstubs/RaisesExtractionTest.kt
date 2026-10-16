package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for the raises sections of the generated entries (design-extraction.md, extract_raises.py; spec-raises.md).
 *
 * - `a Handler without a throw raises nothing` — verifies strlen and substr
 * - `a Handler's throws and specifier classes are raised` — verifies json_decode and intdiv
 * - `a method raises the classes of its Handler` — verifies ArrayIterator::seek and mysqli::query
 * - `a Handler throwing the caller's object keeps no raises section` — verifies assert and Generator::throw
 * - `every raised class is a declared class` — verifies the closure over the set
 */
internal class RaisesExtractionTest {
    @Test
    fun `a Handler without a throw raises nothing`() {
        assertEquals(emptySet<String>(), raisedBy(assertNotNull(PhpStubs.function("strlen"))))
        assertEquals(emptySet<String>(), raisedBy(assertNotNull(PhpStubs.function("substr"))))
    }

    @Test
    fun `a Handler's throws and specifier classes are raised`() {
        assertEquals(setOf("jsonexception", "valueerror"), raisedBy(assertNotNull(PhpStubs.function("json_decode"))))
        assertEquals(
            setOf("arithmeticerror", "divisionbyzeroerror"),
            raisedBy(assertNotNull(PhpStubs.function("intdiv"))),
        )
    }

    @Test
    fun `a method raises the classes of its Handler`() {
        assertEquals(
            setOf("error", "outofboundsexception", "typeerror"),
            raisedBy(assertNotNull(PhpStubs.method("ArrayIterator::seek"))),
        )
        assertEquals(
            setOf("error", "mysqli_sql_exception", "valueerror"),
            raisedBy(assertNotNull(PhpStubs.method("mysqli::query"))),
        )
    }

    @Test
    fun `a Handler throwing the caller's object keeps no raises section`() {
        assertTrue(assertNotNull(PhpStubs.function("assert")).raises.isEmpty())
        assertTrue(assertNotNull(PhpStubs.method("Generator::throw")).raises.isEmpty())
    }

    @Test
    fun `every raised class is a declared class`() {
        val raised = PhpStubs.raises.flatMap { fact -> fact.classes.map { it.name } }.toSet()
        assertTrue(raised.isNotEmpty())
        val undeclared = raised.filter { PhpStubs.clazz(it) == null }
        assertTrue(undeclared.isEmpty(), "Raised but undeclared: $undeclared")
    }

    private fun raisedBy(record: BuiltinRecord<*>): Set<String> =
        record.raises
            .single()
            .classes
            .map { it.name }
            .toSet()
}
