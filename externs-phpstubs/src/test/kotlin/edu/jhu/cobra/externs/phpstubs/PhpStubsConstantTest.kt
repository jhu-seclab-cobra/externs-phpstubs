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
 * - `searchGlobalConst is case-sensitive by default` — verifies exact spelling resolves and a folded one misses
 * - `searchGlobalConst folds when requested` — verifies the case-insensitive over-approximation
 * - `searchGlobalConst returns value and extension` — verifies the typed signature a consumer reads
 * - `searchGlobalConst rejects a member spelling` — verifies a `::` spelling is an argument error
 * - `containsConst resolves a global constant` — verifies the existence check for globals
 * - `containsConst resolves a qualified class constant` — verifies the `Class::NAME` spelling
 * - `containsConst folds a qualified class constant when requested` — verifies folded member spelling
 * - `containsConst misses an unknown name` — verifies absence
 * - `searchClassConst resolves a qualified lookup` — verifies owner plus name resolution
 * - `searchClassConst unqualified returns the first match` — verifies suffix resolution
 * - `searchClassConst folds name when requested` — verifies folded unqualified and qualified lookups
 * - `searchClassConst misses a wrong owner` — verifies a qualified lookup needs the owning class
 * - `getAllConstNames preserves case and excludes class constants` — verifies bulk constant access
 */
internal class PhpStubsConstantTest {
    private val severityError = ClassConstantSubject("Exception", "SEVERITY_ERROR")

    @Test
    fun `searchGlobalConst is case-sensitive by default`() {
        assertNotNull(PhpStubs.searchGlobalConst("PHP_INT_MAX"))
        assertNull(PhpStubs.searchGlobalConst("php_int_max"))
    }

    @Test
    fun `searchGlobalConst folds when requested`() {
        assertEquals(
            "9223372036854775807",
            assertNotNull(PhpStubs.searchGlobalConst("php_int_max", caseSensitive = false)).typedSignature.value,
        )
    }

    @Test
    fun `searchGlobalConst returns value and extension`() {
        val entry = assertNotNull(PhpStubs.searchGlobalConst("E_ALL"))
        assertEquals("32767", entry.typedSignature.value)
        assertEquals("core", entry.extension)
    }

    @Test
    fun `searchGlobalConst rejects a member spelling`() {
        assertFailsWith<IllegalArgumentException> { PhpStubs.searchGlobalConst("Exception::SEVERITY_ERROR") }
    }

    @Test
    fun `containsConst resolves a global constant`() {
        assertTrue(PhpStubs.containsConst("PHP_EOL"))
    }

    @Test
    fun `containsConst resolves a qualified class constant`() {
        assertTrue(PhpStubs.containsConst("\\Exception::SEVERITY_ERROR"))
    }

    @Test
    fun `containsConst folds a qualified class constant when requested`() {
        assertFalse(PhpStubs.containsConst("Exception::severity_error"))
        assertTrue(PhpStubs.containsConst("Exception::severity_error", caseSensitive = false))
    }

    @Test
    fun `containsConst misses an unknown name`() {
        assertFalse(PhpStubs.containsConst("NO_SUCH_CONSTANT"))
    }

    @Test
    fun `searchClassConst resolves a qualified lookup`() {
        val entry = assertNotNull(PhpStubs.searchClassConst("SEVERITY_ERROR", "Exception"))
        assertEquals(severityError, entry.subject)
        assertEquals("1", entry.typedSignature.value)
    }

    @Test
    fun `searchClassConst unqualified returns the first match`() {
        assertEquals(severityError, assertNotNull(PhpStubs.searchClassConst("SEVERITY_ERROR")).subject)
    }

    @Test
    fun `searchClassConst folds name when requested`() {
        assertNull(PhpStubs.searchClassConst("severity_error"))
        assertEquals(severityError, PhpStubs.searchClassConst("severity_error", caseSensitive = false)?.subject)
        assertEquals(severityError, PhpStubs.searchClassConst("severity_error", "EXCEPTION", caseSensitive = false)?.subject)
    }

    @Test
    fun `searchClassConst misses a wrong owner`() {
        assertNull(PhpStubs.searchClassConst("SEVERITY_ERROR", "stdClass"))
    }

    @Test
    fun `getAllConstNames preserves case and excludes class constants`() {
        val names = PhpStubs.getAllConstNames()
        assertTrue("PHP_EOL" in names && "php_eol" !in names && names.none { "::" in it })
    }
}
