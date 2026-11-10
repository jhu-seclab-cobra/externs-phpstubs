package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.Verification
import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Library selection tests.
 * - `catalog roots load generated signed entries` checks every catalog set and its notices.
 * - `catalog matches resource roots` checks that every shipped manifest is selectable.
 * - `each package answers a signed endpoint` checks one method or function per package.
 * - `whereRaw keeps its SQL argument and owner signature` checks the consumer lookup.
 * - `selection preserves order and supports chaining` checks mounting through extend.
 * - `unknown package fails before mounting` checks exact package selection.
 * - `selection leaves the bundled lookup unchanged` checks instance isolation and empty selection.
 */
internal class LibrarySetTest {
    @Test
    fun `catalog roots load generated signed entries`() {
        val context = DocumentSetLoader.load(StubResources.opener(StubResources.VOCABULARY)).vocabulary
        assertEquals(
            PhpStubs.libraries.size,
            PhpStubs.libraries
                .map { it.`package` }
                .toSet()
                .size,
        )
        for (library in PhpStubs.libraries) {
            val set = DocumentSetLoader.load(StubResources.opener(library.root), context)
            assertEquals(Verification.GENERATED, assertNotNull(set.provenance).verification)
            assertTrue(set.entries.isNotEmpty(), library.`package`)
            assertTrue(set.entries.all { it.signature != null && it.condition == null }, library.`package`)
            assertNotNull(StubResources.opener(library.root).open("rejections.json")).close()
            for (upstream in library.upstreams) {
                val name = upstream.substringBefore(' ').substringAfter('/')
                assertNotNull(StubResources.opener(library.root).open("LICENSE-$name.txt"), upstream).close()
            }
        }
    }

    @Test
    fun `catalog matches resource roots`() {
        val directory = Path.of(assertNotNull(javaClass.getResource("/taint-libraries/")).toURI())
        val roots =
            Files.walk(directory).use { paths ->
                paths
                    .filter { it.fileName.toString() == "index.txt" }
                    .map { "/taint-libraries/${directory.relativize(it.parent)}/" }
                    .toList()
                    .toSet()
            }
        assertEquals(roots, PhpStubs.libraries.map { it.root }.toSet())
    }

    @Test
    fun `each package answers a signed endpoint`() {
        for (library in PhpStubs.libraries) {
            val lookup = PhpStubs.withLibraries(library.`package`)
            val record =
                (lookup.methods + lookup.functions).firstOrNull {
                    it.extension == library.`package`.replace('/', '-') &&
                        (it.sinkFacts.isNotEmpty() || it.sourceFacts.isNotEmpty())
                }
            assertNotNull(assertNotNull(record, library.`package`).signature)
        }
    }

    @Test
    fun `whereRaw keeps its SQL argument and owner signature`() {
        val lookup = PhpStubs.withLibraries("laravel/framework")
        val record = assertNotNull(lookup.method("Illuminate\\Database\\Query\\Builder::whereRaw"))
        assertNotNull(record.callableSignature)
        assertNotNull(lookup.clazz("Illuminate\\Database\\Query\\Builder")?.classSignature)
        assertTrue(record.sinkFacts.any { it.port == Port.Argument(0) && it.vulnType == VulnType.SQLI.id })
        assertTrue(record.sinkFacts.none { it.port == Port.Argument(1) })
    }

    @Test
    fun `selection preserves order and supports chaining`() {
        val packages = arrayOf("laravel/framework", "doctrine/dbal")
        val selected = PhpStubs.withLibraries(*packages)
        val extensions = packages.map { it.replace('/', '-') }
        assertEquals(
            extensions,
            selected.methods
                .mapNotNull { it.extension }
                .filter { it in extensions }
                .distinct(),
        )
        val reversed = PhpStubs.withLibraries(*packages.reversedArray())
        assertEquals(
            extensions.reversed(),
            reversed.methods
                .mapNotNull { it.extension }
                .filter { it in extensions }
                .distinct(),
        )
        val expected =
            PhpStubs.with(
                *packages.map { name -> PhpStubs.libraries.single { it.`package` == name }.root }.toTypedArray(),
            )
        assertEquals(expected.sinkFacts, selected.sinkFacts)
        assertEquals(
            selected.methods.toList(),
            PhpStubs
                .withLibraries(packages[0])
                .withLibraries(packages[1])
                .methods
                .toList(),
        )
        val overridden = selected.with("/library-override/").withLibraries("laravel/framework")
        val corrected = assertNotNull(overridden.method("Illuminate\\Database\\Query\\Builder::whereRaw"))
        assertEquals(VulnType.XSS.id, corrected.sinkFacts.single().vulnType)
    }

    @Test
    fun `unknown package fails before mounting`() {
        assertFailsWith<IllegalArgumentException> { PhpStubs.withLibraries("laravel/framework", "missing/package") }
    }

    @Test
    fun `selection leaves the bundled lookup unchanged`() {
        assertNull(PhpStubs.method("Illuminate\\Database\\Query\\Builder::whereRaw"))
        assertEquals(PhpStubs.methods.toList(), PhpStubs.withLibraries().methods.toList())
    }
}
