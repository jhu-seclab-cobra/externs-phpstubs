package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for the throws sections of the generated entries (design-extraction.md, extract_throws.py; spec-throws.md).
 *
 * - `a Handler without a throw throws nothing` — verifies strlen and substr
 * - `a Handler's throws and specifier classes are thrown` — verifies json_decode and intdiv
 * - `a method throws the classes of its Handler` — verifies ArrayIterator::seek and mysqli::query
 * - `a Handler throwing the caller's object keeps no throws section` — verifies assert and Generator::throw
 * - `every thrown class is a declared class` — verifies the closure over the set
 */
internal class ThrowsExtractionTest {
    @Test
    fun `a Handler without a throw throws nothing`() {
        assertEquals(emptySet<String>(), thrownBy(assertNotNull(PhpStubs.function("strlen"))))
        assertEquals(emptySet<String>(), thrownBy(assertNotNull(PhpStubs.function("substr"))))
    }

    @Test
    fun `a Handler's throws and specifier classes are thrown`() {
        assertEquals(setOf("jsonexception", "valueerror"), thrownBy(assertNotNull(PhpStubs.function("json_decode"))))
        assertEquals(
            setOf("arithmeticerror", "divisionbyzeroerror"),
            thrownBy(assertNotNull(PhpStubs.function("intdiv"))),
        )
    }

    @Test
    fun `a method throws the classes of its Handler`() {
        assertEquals(
            setOf("error", "outofboundsexception", "typeerror"),
            thrownBy(assertNotNull(PhpStubs.method("ArrayIterator::seek"))),
        )
        assertEquals(
            setOf("error", "mysqli_sql_exception", "valueerror"),
            thrownBy(assertNotNull(PhpStubs.method("mysqli::query"))),
        )
    }

    @Test
    fun `a Handler throwing the caller's object keeps no throws section`() {
        assertTrue(assertNotNull(PhpStubs.function("assert")).throws.isEmpty())
        assertTrue(assertNotNull(PhpStubs.method("Generator::throw")).throws.isEmpty())
    }

    @Test
    fun `every thrown class is a declared class`() {
        val thrown = PhpStubs.throws.flatMap { fact -> fact.classes.map { it.name } }.toSet()
        assertTrue(thrown.isNotEmpty())
        val undeclared = thrown.filter { PhpStubs.clazz(it) == null }
        assertTrue(undeclared.isEmpty(), "Thrown but undeclared: $undeclared")
    }

    private fun thrownBy(record: BuiltinRecord<*>): Set<String> =
        record.throws
            .single()
            .classes
            .map { it.name }
            .toSet()
}
