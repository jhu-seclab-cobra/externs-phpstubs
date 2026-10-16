package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.DeclaredType
import edu.jhu.cobra.commons.phpmodels.ParameterInfo
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.CallableSignature
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests of the bundled set against the reflection of a PHP 8.5.11 build (design-extraction.md, reflect.php).
 *
 * - `every reflected callable is declared` — verifies completeness by function lookup and method lookup over
 *   the declared hierarchy; the one exception is the Open Gap `closure::__invoke`
 * - `every declared signature admits the reflected one` — verifies parameters and return type; the exceptions are
 *   the Open Gap keyword functions `clone`, `die`, and `exit`
 * - `every reflected class carries the reflected parent and interfaces` — verifies the parent and the transitive
 *   interface set
 */
internal class ReflectionOracleTest {
    private val fixture: List<List<String>> by lazy {
        val stream = assertNotNull(javaClass.getResourceAsStream(FIXTURE), FIXTURE)
        stream.bufferedReader(Charsets.UTF_8).use { reader -> reader.readLines().map { it.split(FIELD_SEPARATOR) } }
    }

    @Test
    fun `every reflected callable is declared`() {
        val undeclared = callables().filter { declaredSignature(it) == null }.map { it.subject }.toSet()
        assertEquals(setOf("closure::__invoke"), undeclared)
    }

    @Test
    fun `every declared signature admits the reflected one`() {
        val rejected =
            callables()
                .filter { reflected -> declaredSignature(reflected)?.let { !it.admits(reflected) } ?: false }
                .map { it.subject }
                .toSet()
        assertEquals(setOf("clone", "die", "exit"), rejected)
    }

    @Test
    fun `every reflected class carries the reflected parent and interfaces`() {
        val classes = fixture.filter { it.first() == CLASS }.map(::ReflectedClass)
        assertTrue(classes.isNotEmpty())
        val differing =
            classes.filter {
                PhpStubs.clazz(it.name)?.classSignature?.parent != it.parent || interfacesOf(it.name) != it.interfaces
            }
        assertTrue(differing.isEmpty(), "Classes whose hierarchy differs from reflection: ${differing.map { it.name }}")
    }

    private fun callables(): List<ReflectedCallable> =
        fixture.filter { it.first() != CLASS }.map(::ReflectedCallable).also { assertTrue(it.isNotEmpty()) }

    // A function by its name; a method by PHP method lookup: its class, then the class's parents and interfaces.
    private fun declaredSignature(reflected: ReflectedCallable): CallableSignature? {
        if (reflected.kind == FUNCTION) return PhpStubs.function(reflected.subject)?.callableSignature
        val (owner, name) = reflected.subject.split("::")
        return lineage(owner).firstNotNullOfOrNull { PhpStubs.method(it, name)?.callableSignature }
    }

    private fun lineage(name: String): List<String> {
        val signature = PhpStubs.clazz(name)?.classSignature ?: return listOf(name)
        return listOf(name) + listOfNotNull(signature.parent).flatMap(::lineage) + signature.interfaces.flatMap(::lineage)
    }

    private fun interfacesOf(name: String): Set<String> {
        val signature = PhpStubs.clazz(name)?.classSignature ?: return emptySet()
        val inherited = listOfNotNull(signature.parent).flatMap(::interfacesOf)
        return (signature.interfaces + signature.interfaces.flatMap(::interfacesOf) + inherited).toSet()
    }

    // The design rule of a kept signature variant: it admits every call the reflected one admits.
    private fun CallableSignature.admits(reflected: ReflectedCallable): Boolean {
        val shared = reflected.params.size
        return params.size >= shared &&
            params.drop(shared).all { it.optional } &&
            params.zip(reflected.params).all { (declared, parameter) -> declared.matches(parameter) } &&
            unionOf(returnType).containsAll(unionOf(reflected.returnType))
    }

    private fun ParameterInfo.matches(reflected: ReflectedParameter): Boolean =
        name == reflected.name &&
            unionOf(type) == unionOf(reflected.type) &&
            optional == reflected.optional &&
            byRef == reflected.byRef &&
            variadic == reflected.variadic

    // PHP compiles `iterable` to `Traversable|array`, the spelling reflection reports.
    private fun unionOf(type: DeclaredType): Set<Set<String>> =
        type.alternatives.flatMap { if (it == setOf(ITERABLE)) ITERABLE_UNION else listOf(it) }.toSet()

    private class ReflectedCallable(
        fields: List<String>,
    ) {
        val kind = fields[0]
        val subject = fields[1]
        val returnType = DeclaredType(fields[2])
        val params = fields.drop(PARAMETERS_START).map(::ReflectedParameter)
    }

    private class ReflectedClass(
        fields: List<String>,
    ) {
        val name = fields[1]
        val parent = fields[2].takeUnless { it == NONE }
        val interfaces = fields[INTERFACES].split(',').filter { it != NONE }.toSet()
    }

    private class ReflectedParameter(
        field: String,
    ) {
        private val parts = field.split(' ')
        val name = parts[0]
        val type = DeclaredType(parts[1])
        val optional = 'o' in parts[2]
        val byRef = 'r' in parts[2]
        val variadic = 'v' in parts[2]
    }

    private companion object {
        // The fixture tools/reflect.php writes from a PHP 8.5.11 build.
        const val FIXTURE = "/reflection/php_8_5_11.tsv"

        // The record format of tools/reflect.php.
        const val FIELD_SEPARATOR = "\t"
        const val FUNCTION = "function"
        const val CLASS = "class"
        const val NONE = "-"
        const val PARAMETERS_START = 3
        const val INTERFACES = 3

        // PHP's expansion of the iterable keyword.
        const val ITERABLE = "iterable"
        val ITERABLE_UNION = listOf(setOf("traversable"), setOf("array"))
    }
}
