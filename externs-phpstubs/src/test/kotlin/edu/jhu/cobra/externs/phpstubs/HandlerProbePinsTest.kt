package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * Pins the 39 PHP reference probes (P01 to P39) of the handler facts to the delivered class facts they rest on. A
 * probe is a PHP 8.5.12 program with its saved output (`src/test/resources/handlers-test/probes.txt`, copied byte for
 * byte). The probes are references of the analyzer's later reads, never taint recall measures; this chain pins the
 * facts each one rests on:
 * - `the probe table covers P01 to P39 once` -- every probe has a saved program, output and at least one pin
 * - `every probe runs the fact pins it rests on` -- each pin is a test of [HandlerFactsTest] asserting the facts
 * - `the saved diagnostics are retained` -- the P01 deprecations, the P24 executed prefix and fatal error, and the P35
 *   compile-time rejection
 * - `the COM probes show COM and variant absent from the reference build` -- source and fixture only
 *
 * The class-chain reads of the probes (inherited methods, descendants, finality of user classes) are pinned by the
 * analyzer module's `BuiltinHierarchyTest`, which cites the probe names.
 */
internal class HandlerProbePinsTest {
    private val facts = HandlerFactsTest()
    private val probes: Map<String, Probe> = readProbes()

    private class Probe(val program: String, val output: String)

    private val standard = { facts.`standard objects use the standard table`() }
    private val exceptions = { facts.`exception classes share the exception table with the standard cast`() }
    private val simpleXml = { facts.`SimpleXML consults the method first for a string and keeps the other casts native`() }
    private val tidy = { facts.`tidy converts natively and never calls the method`() }
    private val com = { facts.`COM converts natively first and falls back to the standard conversion`() }
    private val gmp = { facts.`GMP operations answer an object and the other opcodes fail`() }
    private val date = { facts.`DateTime overrides only the comparison`() }
    private val ffiTables = { facts.`FFI keeps one table per object state`() }
    private val ffiFake = { facts.`FFI and its type objects convert through the fake cast`() }
    private val finality = { facts.`final native classes are final and open ones are not`() }
    private val flags = { facts.`registered enums and interfaces keep their registered flags`() }

    // The facts each probe rests on. P35 is a compile-time rejection that executes nothing, so it rests on none.
    private val pins: Map<String, List<() -> Unit>> = mapOf(
        "P01" to listOf(ffiTables), "P02" to listOf(ffiTables), "P03" to listOf(standard),
        "P04" to listOf(ffiTables, gmp), "P05" to listOf(ffiTables), "P06" to listOf(flags),
        "P07" to listOf(ffiTables, ffiFake), "P08" to listOf(ffiTables, ffiFake), "P09" to listOf(ffiTables, ffiFake),
        "P10" to listOf(date, standard), "P11" to listOf(com), "P12" to listOf(date, standard),
        "P13" to listOf(flags, standard), "P14" to listOf(finality), "P15" to listOf(standard, simpleXml, gmp),
        "P16" to listOf(simpleXml, standard), "P17" to listOf(gmp), "P18" to listOf(simpleXml),
        "P19" to listOf(standard), "P20" to listOf(tidy), "P21" to listOf(standard, exceptions),
        "P22" to listOf(com), "P23" to listOf(ffiTables), "P24" to listOf(finality, standard),
        "P25" to listOf(gmp, finality), "P26" to listOf(simpleXml), "P27" to listOf(standard),
        "P28" to listOf(gmp), "P29" to listOf(ffiTables), "P30" to listOf(gmp), "P31" to listOf(simpleXml, tidy),
        "P32" to listOf(gmp), "P33" to listOf(flags), "P34" to listOf(standard), "P35" to listOf(),
        "P36" to listOf(simpleXml, tidy), "P37" to listOf(flags, finality), "P38" to listOf(gmp, standard),
        "P39" to listOf(standard, finality),
    )

    @Test
    fun `the probe table covers P01 to P39 once`() {
        val expected = (1..39).map { "P%02d".format(it) }

        assertEquals(expected, probes.keys.toList())
        assertEquals(expected.toSet(), pins.keys)
        for ((id, probe) in probes) assertTrue(probe.program.startsWith("<?php"), id)
        assertEquals(listOf("P35"), pins.filterValues { it.isEmpty() }.keys.toList())
    }

    @Test
    fun `every probe runs the fact pins it rests on`() {
        for ((id, list) in pins) {
            for (pin in list) runCatching(pin).onFailure { throw AssertionError("$id: ${it.message}", it) }
        }
    }

    @Test
    fun `the saved diagnostics are retained`() {
        val deprecations = Regex("Deprecated: Calling FFI::new\\(\\) statically is deprecated").findAll(output("P01"))
        assertEquals(3, deprecations.count())
        assertTrue(output("P24").startsWith("bool(true)\nstring(9) \"inherited\"\nbool(true)\n\nFatal error: "))
        assertTrue("Class BadChild cannot extend final class Closure" in output("P24"))
        val compileTime = output("P35")
        assertTrue(compileTime.startsWith("\nFatal error: Cannot use anonymous class in constant expression"))
        assertEquals(1, compileTime.lines().count { it.isNotBlank() && !it.startsWith("#") && it != "Stack trace:" })
        val clean = probes.filterKeys { it !in setOf("P01", "P24", "P35") }
        for ((id, probe) in clean) assertFalse(DIAGNOSTIC.containsMatchIn(probe.output), id)
    }

    @Test
    fun `the COM probes show COM and variant absent from the reference build`() {
        assertEquals("bool(false)\nbool(false)\n", output("P22"))
        assertTrue(output("P11").endsWith("bool(false)\nbool(false)\n"))
    }

    private fun output(id: String) = checkNotNull(probes[id]).output

    private fun readProbes(): Map<String, Probe> {
        val text = checkNotNull(javaClass.getResource("/handlers-test/probes.txt")).readText()
        return PROBE.findAll(text).associate { it.groupValues[1] to Probe(it.groupValues[2], it.groupValues[3]) }
    }

    private companion object {
        val PROBE = Regex(
            "^@@ (P\\d\\d) \\S+\\n@@ program\\n(.*?)\\n@@ output\\n(.*?)\\n(?=@@ P|\\z)",
            setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.MULTILINE),
        )
        val DIAGNOSTIC = Regex("(Deprecated|Warning|Fatal error|Notice): ")
    }
}
