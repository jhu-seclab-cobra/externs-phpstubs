package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.Classifier
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for the php-src hierarchy of the generated class entries (design.md, Class Hierarchy Extraction).
 *
 * - `exception classes declare their php-src parent` — verifies the SPL and engine exception chains
 * - `interfaces carry the interface classifier and their parents` — verifies Throwable and Iterator
 * - `classes declare their php-src interfaces` — verifies Exception, Error, and ArrayObject
 * - `every named parent and interface is a declared class` — verifies the closure over the set
 * - `a class php-src does not declare keeps no hierarchy` — verifies a PECL class
 */
internal class ClassHierarchyTest {
    @Test
    fun `exception classes declare their php-src parent`() {
        val parents =
            mapOf(
                "RuntimeException" to "exception",
                "LogicException" to "exception",
                "InvalidArgumentException" to "logicexception",
                "PDOException" to "runtimeexception",
                "TypeError" to "error",
                "ArgumentCountError" to "typeerror",
                "DivisionByZeroError" to "arithmeticerror",
            )
        for ((name, parent) in parents) {
            assertEquals(parent, signatureOf(name).parent, name)
        }
        assertNull(signatureOf("Exception").parent)
    }

    @Test
    fun `interfaces carry the interface classifier and their parents`() {
        val throwable = signatureOf("Throwable")
        assertEquals(Classifier.INTERFACE, throwable.classifier)
        assertEquals(listOf("stringable"), throwable.interfaces)
        assertEquals(listOf("traversable"), signatureOf("Iterator").interfaces)
    }

    @Test
    fun `classes declare their php-src interfaces`() {
        assertEquals(Classifier.CLASS, signatureOf("Exception").classifier)
        assertEquals(listOf("throwable"), signatureOf("Exception").interfaces)
        assertEquals(listOf("throwable"), signatureOf("Error").interfaces)
        assertEquals(
            listOf("iteratoraggregate", "arrayaccess", "serializable", "countable"),
            signatureOf("ArrayObject").interfaces,
        )
    }

    @Test
    fun `every named parent and interface is a declared class`() {
        val named =
            PhpStubs.classes
                .mapNotNull { it.classSignature }
                .flatMap { listOfNotNull(it.parent) + it.interfaces }
                .toSet()
        val undeclared = named.filter { PhpStubs.clazz(it) == null }
        assertTrue(undeclared.isEmpty(), "Named but undeclared: $undeclared")
    }

    @Test
    fun `a class php-src does not declare keeps no hierarchy`() {
        val imagick = signatureOf("Imagick")
        assertNull(imagick.parent)
        assertTrue(imagick.interfaces.isEmpty())
    }

    private fun signatureOf(name: String) = assertNotNull(assertNotNull(PhpStubs.clazz(name), name).classSignature, name)
}
