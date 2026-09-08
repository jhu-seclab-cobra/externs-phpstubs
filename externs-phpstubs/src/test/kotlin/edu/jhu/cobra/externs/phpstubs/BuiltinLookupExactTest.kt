package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.OriginId
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertSame

/**
 * Tests for the exact-lookup half of [BuiltinLookup], read through the bundled [PhpStubs] companion:
 * one PHP spelling per declaration kind, or owner and name apart, to at most one record.
 * Enumerations: [BuiltinLookupEnumerationTest].
 *
 * - `function lookup folds case and the leading slash` — verifies the spelling is the format library's
 * - `function lookup misses an unknown name and rejects a member spelling` — verifies absence and argument error
 * - `clazz lookup folds case and misses an unknown name` — verifies the class kind
 * - `method lookup accepts both spellings and needs the owner` — verifies the two method forms
 * - `constant lookup is exact and case sensitive` — verifies a global constant resolves only by its spelling
 * - `constant lookup strips the leading slash and rejects a member spelling` — verifies the spelling boundary
 * - `a constant record carries its typed signature and extension` — verifies value and type reach the consumer
 * - `class constant lookup accepts both spellings` — verifies the qualified and split forms
 * - `property lookup accepts both spellings` — verifies the qualified and split forms over an extension set
 * - `variable lookup spells the dollar prefix` — verifies the predefined variable kind
 * - `predefined variables are records with source facts` — verifies the mapped taint sources
 * - `record answers an already built subject` — verifies the subject-keyed lookup
 * - `a name that is not a PHP spelling of the kind is an argument error` — verifies the error class per kind
 */
internal class BuiltinLookupExactTest {
    @Test
    fun `function lookup folds case and the leading slash`() {
        val record = assertNotNull(PhpStubs.function("strlen"))
        assertSame(record, PhpStubs.function("STRLEN"))
        assertSame(record, PhpStubs.function("\\strlen"))
    }

    @Test
    fun `function lookup misses an unknown name and rejects a member spelling`() {
        assertNull(PhpStubs.function("nonexistent_function_xyz"))
        assertFailsWith<IllegalArgumentException> { PhpStubs.function("Exception::getCode") }
    }

    @Test
    fun `clazz lookup folds case and misses an unknown name`() {
        val record = assertNotNull(PhpStubs.clazz("Exception"))
        assertSame(record, PhpStubs.clazz("EXCEPTION"))
        assertSame(record, PhpStubs.clazz("\\Exception"))
        assertNull(PhpStubs.clazz("NonexistentClassXyz"))
    }

    @Test
    fun `method lookup accepts both spellings and needs the owner`() {
        val record = assertNotNull(PhpStubs.method("Exception::getCode"))
        assertSame(record, PhpStubs.method("exception", "getcode"))
        assertEquals("int", record.callableSignature!!.returnType.toString())
        assertNull(PhpStubs.method("ArrayObject::getCode"))
        assertFailsWith<IllegalArgumentException> { PhpStubs.method("getCode") }
    }

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
        assertNull(PhpStubs.property("Exception::\$message"))
    }

    @Test
    fun `variable lookup spells the dollar prefix`() {
        val get = assertNotNull(PhpStubs.variable("\$_GET"))
        assertSame(get, PhpStubs.variable("\$_get"))
        assertNull(PhpStubs.variable("\$_NONEXISTENT_XYZ"))
    }

    @Test
    fun `predefined variables are records with source facts`() {
        val get = assertNotNull(PhpStubs.variable("\$_GET"))
        assertNull(get.signature)
        assertEquals(setOf(OriginId("user-input")), get.sources.single().origins)
        assertSame(get, PhpStubs.record(VariableSubject("_GET")))
        assertEquals(setOf(OriginId("external-input")), assertNotNull(PhpStubs.function("getenv")).sources.single().origins)
    }

    @Test
    fun `record answers an already built subject`() {
        assertSame(PhpStubs.function("substr"), PhpStubs.record(FunctionSubject("substr")))
        assertSame(PhpStubs.method("mysqli::query"), PhpStubs.record(MethodSubject("mysqli", "query")))
        assertNull(PhpStubs.record(FunctionSubject("nonexistent_function_xyz")))
    }

    @Test
    fun `a name that is not a PHP spelling of the kind is an argument error`() {
        val lookups: List<Pair<String, (String) -> Any?>> =
            listOf(
                "function" to { name -> PhpStubs.function(name) },
                "clazz" to { name -> PhpStubs.clazz(name) },
                "constant" to { name -> PhpStubs.constant(name) },
                "method" to { name -> PhpStubs.method(name) },
                "classConstant" to { name -> PhpStubs.classConstant(name) },
                "property" to { name -> PhpStubs.property(name) },
                "variable" to { name -> PhpStubs.variable(name) },
            )
        for ((kind, lookup) in lookups) {
            for (name in listOf("", " ", "a b", "\$")) {
                assertFailsWith<IllegalArgumentException>("$kind($name)") { lookup(name) }
            }
        }
        assertFailsWith<IllegalArgumentException> { PhpStubs.method("", "getCode") }
        assertFailsWith<IllegalArgumentException> { PhpStubs.method("Exception", "") }
        assertFailsWith<IllegalArgumentException> { PhpStubs.classConstant("Exception", "") }
        assertFailsWith<IllegalArgumentException> { PhpStubs.property("Exception", "") }
        assertFailsWith<IllegalArgumentException> { PhpStubs.variable("_GET") }
    }
}
