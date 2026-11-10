package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.Classifier
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
 * - `Request input resolves its trait source` checks signed trait expansion and native hierarchy.
 * - `Client get resolves its trait sink` checks the effective SSRF endpoint and signed trait owner.
 * - `Request file keeps the source from the upstream union` checks the source disagreement rule.
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
    fun `Request input resolves its trait source`() {
        val lookup = PhpStubs.withLibraries("laravel/framework")
        val request = assertNotNull(lookup.clazz("Illuminate\\Http\\Request")?.classSignature)
        assertEquals("symfony\\component\\httpfoundation\\request", request.parent)
        assertEquals(listOf("illuminate\\contracts\\support\\arrayable", "arrayaccess"), request.interfaces)
        val trait = "Illuminate\\Http\\Concerns\\InteractsWithInput"
        assertEquals(Classifier.TRAIT, lookup.clazz(trait)?.classSignature?.classifier)
        for (owner in listOf("Illuminate\\Http\\Request", trait)) {
            val record = assertNotNull(lookup.method(owner, "input"))
            assertNotNull(record.callableSignature)
            assertTrue(record.sourceFacts.any { SourceKind.USER_INPUT.id in it.sourceKinds })
        }
    }

    @Test
    fun `Client get resolves its trait sink`() {
        val lookup = PhpStubs.withLibraries("guzzlehttp/guzzle")
        val signature = assertNotNull(lookup.clazz("GuzzleHttp\\Client")?.classSignature)
        assertTrue("guzzlehttp\\clientinterface" in signature.interfaces)
        assertNotNull(lookup.clazz("GuzzleHttp\\ClientInterface")?.classSignature)
        assertEquals(Classifier.TRAIT, lookup.clazz("GuzzleHttp\\ClientTrait")?.classSignature?.classifier)
        for (owner in listOf("GuzzleHttp\\Client", "GuzzleHttp\\ClientTrait")) {
            val record = assertNotNull(lookup.method(owner, "get"))
            assertNotNull(record.callableSignature)
            assertTrue(record.sinkFacts.any { it.port == Port.Argument(0) && it.vulnType == VulnType.SSRF.id })
        }
    }

    @Test
    fun `Request file keeps the source from the upstream union`() {
        val record = assertNotNull(PhpStubs.withLibraries("laravel/framework").method("Illuminate\\Http\\Request::file"))
        assertTrue(record.sourceFacts.any { SourceKind.USER_INPUT.id in it.sourceKinds })
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
