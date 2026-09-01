package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.Classifier
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.PropertySubject
import edu.jhu.cobra.commons.phpmodels.Visibility
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull

/**
 * Tests for [StubEntry] invariants and its typed signature accessors.
 * Entries come from `/models-test/`.
 *
 * - `entry exposes subject model and extension` — verifies the three fields of a loaded entry
 * - `subject differing from model subject is rejected` — verifies the `model.subject == subject` invariant
 * - `blank extension is rejected` — verifies the non-blank extension invariant
 * - `function entry exposes callable signature` — verifies params and return type of a function
 * - `method entry exposes callable signature` — verifies return type of a method
 * - `class entry exposes class signature` — verifies classifier, parent, and interfaces of a class
 * - `constant entry exposes typed signature` — verifies type and value of a global constant
 * - `class constant entry exposes typed signature` — verifies type and value of a class constant
 * - `property entry exposes property signature` — verifies type and visibility of a property
 */
internal class StubEntryTest {
    private val registry: StubRegistry by lazy { StubLoader.loadAll("/models-test/") }

    private fun function(name: String): StubEntry<FunctionSubject> = assertNotNull(registry.functions[FunctionSubject(name)])

    @Test
    fun `entry exposes subject model and extension`() {
        val entry = function("strlen")
        assertEquals(FunctionSubject("strlen"), entry.subject)
        assertEquals(FunctionSubject("strlen"), entry.model.subject)
        assertEquals("standard", entry.extension)
    }

    @Test
    fun `subject differing from model subject is rejected`() {
        val entry = function("strlen")
        assertFailsWith<IllegalArgumentException> {
            StubEntry(FunctionSubject("substr"), entry.model, entry.extension)
        }
    }

    @Test
    fun `blank extension is rejected`() {
        val entry = function("strlen")
        assertFailsWith<IllegalArgumentException> {
            StubEntry(entry.subject, entry.model, " ")
        }
    }

    @Test
    fun `function entry exposes callable signature`() {
        val signature = function("substr").callableSignature
        assertEquals(listOf("string", "offset", "length"), signature.params.map { it.name })
        assertEquals("string", signature.returnType.toString())
    }

    @Test
    fun `method entry exposes callable signature`() {
        val entry = assertNotNull(registry.methods[MethodSubject("Exception", "getMessage")])
        assertEquals("string", entry.callableSignature.returnType.toString())
    }

    @Test
    fun `class entry exposes class signature`() {
        val entry = assertNotNull(registry.classes[ClassSubject("RuntimeException")])
        val signature = entry.classSignature
        assertEquals(Classifier.CLASS, signature.classifier)
        assertEquals("exception", signature.parent)
        assertEquals(listOf("throwable"), assertNotNull(registry.classes[ClassSubject("Exception")]).classSignature.interfaces)
    }

    @Test
    fun `constant entry exposes typed signature`() {
        val entry = assertNotNull(registry.constants[ConstantSubject("PHP_INT_MAX")])
        assertEquals("int", entry.typedSignature.type.toString())
        assertEquals("9223372036854775807", entry.typedSignature.value)
    }

    @Test
    fun `class constant entry exposes typed signature`() {
        val entry = assertNotNull(registry.classConstants[ClassConstantSubject("Exception", "SEVERITY_ERROR")])
        assertEquals("int", entry.typedSignature.type.toString())
        assertEquals("1", entry.typedSignature.value)
    }

    @Test
    fun `property entry exposes property signature`() {
        val entry = assertNotNull(registry.properties[PropertySubject("Exception", "message")])
        assertEquals("string", entry.propertySignature.type.toString())
        assertEquals(Visibility.PROTECTED, entry.propertySignature.visibility)
    }
}
