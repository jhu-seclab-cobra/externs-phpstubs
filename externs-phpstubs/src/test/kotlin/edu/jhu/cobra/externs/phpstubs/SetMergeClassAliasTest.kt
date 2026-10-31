package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.Verification
import kotlin.test.Test
import kotlin.test.assertContains
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertSame

/**
 * Tests for the class-alias key step of [SetMerge] (spec-merge.md) and for the enumeration of [PhpStubs.classes].
 *
 * The PHP fact behind the bundled cases, PHP 8.5.11 (local php 8.5.12):
 * ```php
 * <?php
 * var_dump(new ReflectionClass('Dom\DOMException') == new ReflectionClass('DOMException'));
 * echo (new ReflectionClass('Dom\DOMException'))->getName();
 * // bool(true)
 * // DOMException
 * ```
 *
 * - `a class alias reads the record of its declaring class` — verifies the alias key returns the same record object
 * - `a class alias is no declaration subject` — verifies the shared record map holds the declaration subject only
 * - `a class alias colliding with a declaration subject fails the merge` — verifies the collision rule
 * - `two classes stating one class alias fail the merge` — verifies the collision rule between aliases
 * - `a signature replacement without aliases removes the keys` — verifies aliases follow the signature in force
 * - `enumeration lists a class with aliases once` — verifies the primary-key view
 * - `the bundled DOMException is reachable under both spellings` — verifies the extraction output end to end
 */
internal class SetMergeClassAliasTest {
    private val declared = ClassSubject("domexception")
    private val alias = ClassSubject.parse("Dom\\DOMException")

    private fun classEntry(
        subject: String,
        name: String,
        vararg aliases: String,
    ): String =
        "- subject: {class: $subject}\n  signature: {classifier: class, name: $name, aliases: [${aliases.joinToString()}]}\n"

    private fun merge(vararg documents: String): SetMerge =
        SetMerge.of(documents.mapIndexed { i, d -> TestSets.mount(i, Verification.MANUAL, d) })

    @Test
    fun `a class alias reads the record of its declaring class`() {
        val merge = merge(classEntry("domexception", "DOMException", "dom\\domexception"))
        val record = assertNotNull(merge.classes[declared])
        assertSame(record, merge.classes[alias])
        assertEquals(declared, record.subject)
    }

    @Test
    fun `a class alias is no declaration subject`() {
        val merge = merge(classEntry("domexception", "DOMException", "dom\\domexception"))
        assertNull(merge.records[alias])
        assertNotNull(merge.records[declared])
    }

    @Test
    fun `a class alias colliding with a declaration subject fails the merge`() {
        val documents = classEntry("a", "A", "b") + classEntry("b", "B")
        val failure = assertFailsWith<StubIndexInvalidException> { merge(documents) }
        assertContains(failure.message!!, "'b'")
    }

    @Test
    fun `two classes stating one class alias fail the merge`() {
        val documents = classEntry("a", "A", "x\\c") + classEntry("b", "B", "x\\c")
        assertFailsWith<StubIndexInvalidException> { merge(documents) }
    }

    @Test
    fun `a signature replacement without aliases removes the keys`() {
        val first = TestSets.mount(0, Verification.GENERATED, classEntry("domexception", "DOMException", "dom\\domexception"))
        val replacing = TestSets.mount(1, Verification.MANUAL, classEntry("domexception", "DOMException"))
        val merge = SetMerge.of(listOf(first, replacing))
        assertNotNull(merge.classes[declared])
        assertNull(merge.classes[alias])
    }

    @Test
    fun `enumeration lists a class with aliases once`() {
        val stubs = PhpStubs.with("/consumer-test/")
        val listed = PhpStubs.classes.filter { it.subject == declared }
        assertEquals(1, listed.size)
        assertEquals(PhpStubs.classes.size, PhpStubs.classes.map { it.subject }.toSet().size)
        assertEquals(PhpStubs.classes.size, stubs.classes.size)
    }

    @Test
    fun `the bundled DOMException is reachable under both spellings`() {
        val canonical = assertNotNull(PhpStubs.clazz("DOMException"))
        assertSame(canonical, PhpStubs.clazz("Dom\\DOMException"))
        assertSame(canonical, PhpStubs.clazz("\\dom\\domexception"))
        assertEquals(declared, canonical.subject)
        assertNull(PhpStubs.record(alias))
    }
}
