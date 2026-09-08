package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertSame
import kotlin.test.assertTrue

/**
 * Tests for constant lookups on the bundled [PhpStubs] merge: global constants, class constants, and properties.
 *
 * - `constant lookup is exact and case sensitive` — verifies a global constant resolves only by its spelling
 * - `constant lookup strips the leading slash and rejects a member spelling` — verifies the spelling boundary
 * - `a constant record carries its typed signature and extension` — verifies value and type reach the consumer
 * - `class constant lookup accepts both spellings` — verifies the qualified and split forms
 * - `property lookup accepts both spellings` — verifies the qualified and split forms over an extension set
 * - `constant enumerations are non-empty and keyed by subject` — verifies bulk access
 */
internal class PhpStubsConstantTest {
    @Test
    fun `constant lookup is exact and case sensitive`() {
        assertNotNull(PhpStubs.constant("PHP_INT_MAX"))
        assertNull(PhpStubs.constant("php_int_max"))
        assertNull(PhpStubs.constant("NONEXISTENT_CONSTANT_XYZ"))
    }

    @Test
    fun `constant lookup strips the leading slash and rejects a member spelling`() {
        assertSame(PhpStubs.constant("E_ALL"), PhpStubs.constant("\\E_ALL"))
        assertFailsWith<IllegalArgumentException> { PhpStubs.constant("Exception::SEVERITY_ERROR") }
    }

    @Test
    fun `a constant record carries its typed signature and extension`() {
        val all = assertNotNull(PhpStubs.constant("E_ALL"))
        assertEquals("core", all.extension)
        assertEquals("32767", assertNotNull(all.typedSignature).value)
        assertEquals("9223372036854775807", assertNotNull(PhpStubs.constant("PHP_INT_MAX")).typedSignature!!.value)
    }

    @Test
    fun `class constant lookup accepts both spellings`() {
        val record = assertNotNull(PhpStubs.classConstant("Exception::SEVERITY_ERROR"))
        assertSame(record, PhpStubs.classConstant("exception", "SEVERITY_ERROR"))
        assertSame(record, PhpStubs.record(ClassConstantSubject("Exception", "SEVERITY_ERROR")))
        assertEquals("1", record.typedSignature!!.value)
        assertNull(PhpStubs.classConstant("Exception::severity_error"))
    }

    @Test
    fun `property lookup accepts both spellings`() {
        val extended = PhpStubs.with("/extension-test/")
        val record = assertNotNull(extended.property("Exception::\$message"))
        assertSame(record, extended.property("Exception", "message"))
        assertNotNull(record.propertySignature)
        assertNull(extended.property("Exception::\$nonexistent"))
        assertTrue(PhpStubs.properties.isEmpty())
    }

    @Test
    fun `constant enumerations are non-empty and keyed by subject`() {
        assertTrue(PhpStubs.constants.size > 200)
        assertTrue(PhpStubs.classConstants.all { it.signature != null })
        assertTrue(PhpStubs.constants.all { PhpStubs.record(it.subject) === it })
    }
}
