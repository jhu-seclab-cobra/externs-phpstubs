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
 * - `containsFunction finds a standard function` — verifies a known built-in resolves
 * - `containsFunction folds case` — verifies function lookup is case-insensitive
 * - `containsFunction strips the leading namespace slash` — verifies a fully qualified spelling resolves
 * - `containsFunction finds keyword constructs` — verifies language constructs are functions
 * - `containsFunction misses an unknown name` — verifies an unregistered name is absent
 * - `containsFunction rejects a member spelling` — verifies a `::` spelling is an argument error
 * - `containsClass finds built-in scalar and legacy classes` — verifies the three class documents load
 * - `containsClass misses an unknown name` — verifies an unregistered class is absent
 * - `containsMethod resolves qualified and unqualified names` — verifies both lookup forms
 * - `containsMethod misses a wrong owner` — verifies a qualified lookup needs the owning class
 * - `findFunction returns entry with extension and signature` — verifies the entry a consumer reads
 * - `findFunction exposes declared propagation` — verifies the body reaches the consumer
 * - `findFunction exposes a variadic tail` — verifies the generated variadic mark decodes
 * - `findFunction returns null for unknown name` — verifies absence is null
 * - `findClass returns the keyword extension for exit` — verifies language-construct provenance
 * - `findMethod returns the qualified subject` — verifies the entry carries owner and name
 * - `findMethod unqualified returns the first match in load order` — verifies suffix resolution
 * - `functionNames holds folded names including keywords` — verifies bulk function access
 * - `classNames holds folded names including scalar types` — verifies bulk class access
 * - `methodNames spells owner and name` — verifies the `owner::name` spelling
 * - `keywordFunctionNames is the keyword document` — verifies the closed keyword set
 * - `scalarTypeNames is the scalar document` — verifies the closed scalar set
 */
internal class PhpStubsTest {
    @Test
    fun `containsFunction finds a standard function`() {
        assertTrue(PhpStubs.containsFunction("strlen"))
    }

    @Test
    fun `containsFunction folds case`() {
        assertTrue(PhpStubs.containsFunction("STRLEN"))
    }

    @Test
    fun `containsFunction strips the leading namespace slash`() {
        assertTrue(PhpStubs.containsFunction("\\strlen"))
    }

    @Test
    fun `containsFunction finds keyword constructs`() {
        assertTrue(PhpStubs.containsFunction("echo") && PhpStubs.containsFunction("include_once"))
    }

    @Test
    fun `containsFunction misses an unknown name`() {
        assertFalse(PhpStubs.containsFunction("no_such_function"))
    }

    @Test
    fun `containsFunction rejects a member spelling`() {
        assertFailsWith<IllegalArgumentException> { PhpStubs.containsFunction("Exception::getMessage") }
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
    fun `findFunction returns entry with extension and signature`() {
        val entry = assertNotNull(PhpStubs.findFunction("strlen"))
        assertEquals("standard", entry.extension)
        assertEquals("int", entry.callableSignature.returnType.toString())
    }

    @Test
    fun `findFunction exposes declared propagation`() {
        val flows = assertNotNull(assertNotNull(PhpStubs.findFunction("substr")).model.body.propagation)
        assertEquals(listOf(Port.Argument(0) to Port.Return), flows.map { it.from to it.to })
    }

    @Test
    fun `findFunction exposes a variadic tail`() {
        val params = assertNotNull(PhpStubs.findFunction("sprintf")).callableSignature.params
        assertTrue(params.last().variadic)
    }

    @Test
    fun `findFunction returns null for unknown name`() {
        assertNull(PhpStubs.findFunction("no_such_function"))
    }

    @Test
    fun `findClass returns the keyword extension for exit`() {
        assertEquals("keyword", assertNotNull(PhpStubs.findClass("exit")).extension)
    }

    @Test
    fun `findMethod returns the qualified subject`() {
        val entry = assertNotNull(PhpStubs.findMethod("getCode", "\\Exception"))
        assertEquals(MethodSubject("exception", "getcode"), entry.subject)
        assertEquals("int", entry.callableSignature.returnType.toString())
    }

    @Test
    fun `findMethod unqualified returns the first match in load order`() {
        assertEquals(MethodSubject("exception", "getmessage"), assertNotNull(PhpStubs.findMethod("GETMESSAGE")).subject)
    }

    @Test
    fun `functionNames holds folded names including keywords`() {
        val names = PhpStubs.functionNames
        assertTrue("strlen" in names && "isset" in names && names.none { it != it.lowercase() })
    }

    @Test
    fun `classNames holds folded names including scalar types`() {
        val names = PhpStubs.classNames
        assertTrue("exception" in names && "string" in names && names.none { it != it.lowercase() })
    }

    @Test
    fun `methodNames spells owner and name`() {
        assertTrue("exception::getmessage" in PhpStubs.methodNames)
    }

    @Test
    fun `keywordFunctionNames is the keyword document`() {
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
            PhpStubs.keywordFunctionNames,
        )
        assertTrue(PhpStubs.keywordFunctionNames.all { PhpStubs.findFunction(it)?.subject == FunctionSubject(it) })
    }

    @Test
    fun `scalarTypeNames is the scalar document`() {
        assertEquals(setOf("int", "float", "string", "bool", "array"), PhpStubs.scalarTypeNames)
    }
}
