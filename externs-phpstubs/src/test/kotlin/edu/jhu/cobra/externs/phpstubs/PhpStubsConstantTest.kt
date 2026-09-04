package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [PhpStubs] constant lookups: exact by default, folded on request.
 *
 * - `findConstant is case-sensitive by default` — verifies exact spelling resolves and a folded one misses
 * - `findConstant folds when requested` — verifies the case-insensitive over-approximation
 * - `findConstant returns value and extension` — verifies the typed signature a consumer reads
 * - `findConstant rejects a member spelling` — verifies a `::` spelling is an argument error
 * - `containsConstant resolves a global constant` — verifies the existence check for globals
 * - `containsConstant resolves a qualified class constant` — verifies the `Class::NAME` spelling
 * - `containsConstant folds a qualified class constant when requested` — verifies folded member spelling
 * - `containsConstant misses an unknown name` — verifies absence
 * - `findClassConstant resolves a qualified lookup` — verifies owner plus name resolution
 * - `findClassConstant unqualified returns the first match` — verifies suffix resolution
 * - `findClassConstant folds name when requested` — verifies folded unqualified and qualified lookups
 * - `findClassConstant misses a wrong owner` — verifies a qualified lookup needs the owning class
 * - `constantNames preserves case and excludes class constants` — verifies bulk constant access
 */
internal class PhpStubsConstantTest {
    private val severityError = ClassConstantSubject("Exception", "SEVERITY_ERROR")

    @Test
    fun `findConstant is case-sensitive by default`() {
        assertNotNull(PhpStubs.findConstant("PHP_INT_MAX"))
        assertNull(PhpStubs.findConstant("php_int_max"))
    }

    @Test
    fun `findConstant folds when requested`() {
        assertEquals(
            "9223372036854775807",
            assertNotNull(PhpStubs.findConstant("php_int_max", caseSensitive = false)).typedSignature.value,
        )
    }

    @Test
    fun `findConstant returns value and extension`() {
        val entry = assertNotNull(PhpStubs.findConstant("E_ALL"))
        assertEquals("32767", entry.typedSignature.value)
        assertEquals("core", entry.extension)
    }

    @Test
    fun `findConstant rejects a member spelling`() {
        assertFailsWith<IllegalArgumentException> { PhpStubs.findConstant("Exception::SEVERITY_ERROR") }
    }

    @Test
    fun `containsConstant resolves a global constant`() {
        assertTrue(PhpStubs.containsConstant("PHP_EOL"))
    }

    @Test
    fun `containsConstant resolves a qualified class constant`() {
        assertTrue(PhpStubs.containsConstant("\\Exception::SEVERITY_ERROR"))
    }

    @Test
    fun `containsConstant folds a qualified class constant when requested`() {
        assertFalse(PhpStubs.containsConstant("Exception::severity_error"))
        assertTrue(PhpStubs.containsConstant("Exception::severity_error", caseSensitive = false))
    }

    @Test
    fun `containsConstant misses an unknown name`() {
        assertFalse(PhpStubs.containsConstant("NO_SUCH_CONSTANT"))
    }

    @Test
    fun `findClassConstant resolves a qualified lookup`() {
        val entry = assertNotNull(PhpStubs.findClassConstant("SEVERITY_ERROR", "Exception"))
        assertEquals(severityError, entry.subject)
        assertEquals("1", entry.typedSignature.value)
    }

    @Test
    fun `findClassConstant unqualified returns the first match`() {
        assertEquals(severityError, assertNotNull(PhpStubs.findClassConstant("SEVERITY_ERROR")).subject)
    }

    @Test
    fun `findClassConstant folds name when requested`() {
        assertNull(PhpStubs.findClassConstant("severity_error"))
        assertEquals(severityError, PhpStubs.findClassConstant("severity_error", caseSensitive = false)?.subject)
        assertEquals(severityError, PhpStubs.findClassConstant("severity_error", "EXCEPTION", caseSensitive = false)?.subject)
    }

    @Test
    fun `findClassConstant misses a wrong owner`() {
        assertNull(PhpStubs.findClassConstant("SEVERITY_ERROR", "stdClass"))
    }

    @Test
    fun `constantNames preserves case and excludes class constants`() {
        val names = PhpStubs.constantNames
        assertTrue("PHP_EOL" in names && "php_eol" !in names && names.none { "::" in it })
    }
}
