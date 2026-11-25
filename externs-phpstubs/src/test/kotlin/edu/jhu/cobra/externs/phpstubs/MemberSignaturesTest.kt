package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.Visibility
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull

/**
 * Tests for the typed property and typed class constant entries of the generated documents, extracted from the
 * php-src 8.5.11 stubs (design-extraction.md, extract_members.py).
 *
 * - `a typed property declares its type and visibility` — verifies a scalar, a class and an inherited-name case
 * - `an untyped property has no entry` — verifies that a declaration without a type states no signature
 * - `a typed class constant declares its type` — verifies a constant of a class and one of an interface
 * - `class constants differing only by case are two entries` — verifies the case-sensitive member name
 */
internal class MemberSignaturesTest {
    @Test
    fun `a typed property declares its type and visibility`() {
        val file = assertNotNull(PhpStubs.property("Exception", "file")?.propertySignature)
        assertEquals("string", file.type.raw)
        assertEquals(Visibility.PROTECTED, file.visibility)
        assertEquals("int", assertNotNull(PhpStubs.property("Exception::\$line")?.propertySignature).type.raw)
        assertEquals("?DateTimeInterface", assertNotNull(PhpStubs.property("DatePeriod", "start")?.propertySignature).type.raw)
    }

    @Test
    fun `an untyped property has no entry`() {
        assertNull(PhpStubs.property("Exception", "message"))
    }

    @Test
    fun `a typed class constant declares its type`() {
        assertEquals("string", assertNotNull(PhpStubs.classConstant("DateTimeInterface", "ATOM")?.typedSignature).type.raw)
        assertEquals("int", assertNotNull(PhpStubs.classConstant("ArrayObject::STD_PROP_LIST")?.typedSignature).type.raw)
    }

    @Test
    fun `class constants differing only by case are two entries`() {
        val upper = assertNotNull(PhpStubs.classConstant("SNMP", "VERSION_2C"))
        val lower = assertNotNull(PhpStubs.classConstant("SNMP", "VERSION_2c"))
        assertEquals(setOf("VERSION_2C", "VERSION_2c"), setOf(upper.subject.name, lower.subject.name))
    }
}
