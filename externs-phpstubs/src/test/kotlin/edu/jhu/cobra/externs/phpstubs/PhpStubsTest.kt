package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.Port
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for the [PhpStubs] facade over the bundled corpus: functions, classes, methods, and bulk access.
 * Constant lookups: [PhpStubsConstantTest].
 *
 * - `containsFunc finds a standard function` — verifies a known built-in resolves
 * - `containsFunc folds case` — verifies function lookup is case-insensitive
 * - `containsFunc strips the leading namespace slash` — verifies a fully qualified spelling resolves
 * - `containsFunc finds keyword constructs` — verifies language constructs are functions
 * - `containsFunc misses an unknown name` — verifies an unregistered name is absent
 * - `containsFunc rejects a member spelling` — verifies a `::` spelling is an argument error
 * - `containsClass finds built-in scalar and legacy classes` — verifies the three class documents load
 * - `containsClass misses an unknown name` — verifies an unregistered class is absent
 * - `containsMethod resolves qualified and unqualified names` — verifies both lookup forms
 * - `containsMethod misses a wrong owner` — verifies a qualified lookup needs the owning class
 * - `searchFunc returns entry with extension and signature` — verifies the entry a consumer reads
 * - `searchFunc exposes declared propagation` — verifies the body reaches the consumer
 * - `searchFunc exposes a variadic tail` — verifies the generated variadic mark decodes
 * - `searchFunc returns null for unknown name` — verifies absence is null
 * - `searchClass returns the keyword extension for exit` — verifies language-construct provenance
 * - `searchMethod returns the qualified subject` — verifies the entry carries owner and name
 * - `searchMethod unqualified returns the first match in load order` — verifies suffix resolution
 * - `getAllFuncNames holds folded names including keywords` — verifies bulk function access
 * - `getAllClassNames holds folded names including scalar types` — verifies bulk class access
 * - `getAllMethodNames spells owner and name` — verifies the `owner::name` spelling
 * - `getKeywordFuncNames is the keyword document` — verifies the closed keyword set
 * - `getScalarTypeNames is the scalar document` — verifies the closed scalar set
 */
internal class PhpStubsTest {
    @Test
    fun `containsFunc finds a standard function`() {
        assertTrue(PhpStubs.containsFunc("strlen"))
    }

    @Test
    fun `containsFunc folds case`() {
        assertTrue(PhpStubs.containsFunc("STRLEN"))
    }

    @Test
    fun `containsFunc strips the leading namespace slash`() {
        assertTrue(PhpStubs.containsFunc("\\strlen"))
    }

    @Test
    fun `containsFunc finds keyword constructs`() {
        assertTrue(PhpStubs.containsFunc("echo") && PhpStubs.containsFunc("include_once"))
    }

    @Test
    fun `containsFunc misses an unknown name`() {
        assertFalse(PhpStubs.containsFunc("no_such_function"))
    }

    @Test
    fun `containsFunc rejects a member spelling`() {
        assertFailsWith<IllegalArgumentException> { PhpStubs.containsFunc("Exception::getMessage") }
    }

    @Test
    fun `containsClass finds built-in scalar and legacy classes`() {
        assertTrue(PhpStubs.containsClass("Exception") && PhpStubs.containsClass("int") && PhpStubs.containsClass("resource"))
    }

    @Test
    fun `containsClass misses an unknown name`() {
        assertFalse(PhpStubs.containsClass("NoSuchClass"))
    }

    @Test
    fun `containsMethod resolves qualified and unqualified names`() {
        assertTrue(PhpStubs.containsMethod("getMessage", "Exception") && PhpStubs.containsMethod("getMessage"))
    }

    @Test
    fun `containsMethod misses a wrong owner`() {
        assertFalse(PhpStubs.containsMethod("getMessage", "stdClass"))
    }

    @Test
    fun `searchFunc returns entry with extension and signature`() {
        val entry = assertNotNull(PhpStubs.searchFunc("strlen"))
        assertEquals("standard", entry.extension)
        assertEquals("int", entry.callableSignature.returnType.toString())
    }

    @Test
    fun `searchFunc exposes declared propagation`() {
        val flows = assertNotNull(assertNotNull(PhpStubs.searchFunc("substr")).model.body.propagation)
        assertEquals(listOf(Port.Argument(0) to Port.Return), flows.map { it.from to it.to })
    }

    @Test
    fun `searchFunc exposes a variadic tail`() {
        val params = assertNotNull(PhpStubs.searchFunc("sprintf")).callableSignature.params
        assertTrue(params.last().variadic)
    }

    @Test
    fun `searchFunc returns null for unknown name`() {
        assertNull(PhpStubs.searchFunc("no_such_function"))
    }

    @Test
    fun `searchClass returns the keyword extension for exit`() {
        assertEquals("keyword", assertNotNull(PhpStubs.searchClass("exit")).extension)
    }

    @Test
    fun `searchMethod returns the qualified subject`() {
        val entry = assertNotNull(PhpStubs.searchMethod("getCode", "\\Exception"))
        assertEquals(MethodSubject("exception", "getcode"), entry.subject)
        assertEquals("int", entry.callableSignature.returnType.toString())
    }

    @Test
    fun `searchMethod unqualified returns the first match in load order`() {
        assertEquals(MethodSubject("exception", "getmessage"), assertNotNull(PhpStubs.searchMethod("GETMESSAGE")).subject)
    }

    @Test
    fun `getAllFuncNames holds folded names including keywords`() {
        val names = PhpStubs.getAllFuncNames()
        assertTrue("strlen" in names && "isset" in names && names.none { it != it.lowercase() })
    }

    @Test
    fun `getAllClassNames holds folded names including scalar types`() {
        val names = PhpStubs.getAllClassNames()
        assertTrue("exception" in names && "string" in names && names.none { it != it.lowercase() })
    }

    @Test
    fun `getAllMethodNames spells owner and name`() {
        assertTrue("exception::getmessage" in PhpStubs.getAllMethodNames())
    }

    @Test
    fun `getKeywordFuncNames is the keyword document`() {
        assertEquals(
            setOf(
                "echo",
                "empty",
                "eval",
                "exit",
                "die",
                "isset",
                "print",
                "unset",
                "clone",
                "instanceof",
                "include",
                "include_once",
                "require",
                "require_once",
            ),
            PhpStubs.getKeywordFuncNames(),
        )
        assertTrue(PhpStubs.getKeywordFuncNames().all { PhpStubs.searchFunc(it)?.subject == FunctionSubject(it) })
    }

    @Test
    fun `getScalarTypeNames is the scalar document`() {
        assertEquals(setOf("int", "float", "string", "bool", "array"), PhpStubs.getScalarTypeNames())
    }
}
