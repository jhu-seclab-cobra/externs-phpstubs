package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.CharacterBound
import edu.jhu.cobra.commons.phpmodels.CharacterClass
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.VulnTypeId
import org.junit.jupiter.api.io.TempDir
import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [PhpStubs]: the bundled merge in Mount Order and the construction of consumer set merges through
 * [PhpStubs.with] and [PhpStubs.plus]. The read surface: [BuiltinLookupExactTest], [BuiltinLookupEnumerationTest].
 *
 * - `keyword constructs and scalar classes are records` — verifies the language documents load
 * - `a record carries extension, signature, and the value unit in force` — verifies the manual rule outranks
 * - `a merged record carries the character bound of its value unit` — verifies basename's bound survives the merge
 * - `taint facts speak the canonical vocabulary` — verifies sinks, sanitizers, and conditions after mapping
 * - `taint rules outrank taint for the same key` — verifies the later manual set replaces the generated one
 * - `a lookup over the same mounts holds equal records` — verifies equal entries in force give equal records
 * - `with mounts a classpath consumer set after the bundled ones` — verifies override and addition
 * - `a consumer set without provenance mounts as manual` — verifies it replaces a bundled manual entry
 * - `a consumer set with generated provenance loses to a bundled manual entry` — verifies rank over order
 * - `later consumer roots override earlier ones` — verifies supplied order among consumer sets
 * - `plus chains like with` — verifies the operator form
 * - `with mounts a directory consumer set` — verifies the filesystem opener
 * - `a consumer set failure surfaces from the mounting call` — verifies error classification
 * - `a directory consumer set names the absent document` — verifies absence under the filesystem opener
 */
internal class PhpStubsTest {
    @Test
    fun `keyword constructs and scalar classes are records`() {
        for (name in listOf("echo", "isset", "require_once", "instanceof")) {
            assertEquals("keyword", assertNotNull(PhpStubs.function(name), name).extension)
        }
        for (name in listOf("int", "float", "string", "bool", "array")) {
            assertEquals("scalar", assertNotNull(PhpStubs.clazz(name), name).extension)
        }
        assertEquals("keyword", assertNotNull(PhpStubs.clazz("exit")).extension)
        assertEquals("legacy", assertNotNull(PhpStubs.clazz("resource")).extension)
    }

    @Test
    fun `a record carries extension, signature, and the value unit in force`() {
        val strlen = assertNotNull(PhpStubs.function("strlen"))
        assertEquals("core", strlen.extension)
        assertEquals("int", assertNotNull(strlen.callableSignature).returnType.toString())
        assertEquals(ReturnKind.NUM, strlen.returns.single().kind)
        assertEquals(listOf(Port.Argument(0) to Port.Return), strlen.flows.map { it.from to it.to })
        assertTrue(
            assertNotNull(PhpStubs.function("sprintf"))
                .callableSignature!!
                .params
                .last()
                .variadic,
        )
    }

    @Test
    fun `a merged record carries the character bound of its value unit`() {
        val basename = assertNotNull(PhpStubs.function("basename"))
        val bound = CharacterBound(of = setOf(Port.Argument(0)), within = CharacterClass("[^/]"))
        assertEquals(listOf(bound), basename.characters.map { it.bound })
    }

    @Test
    fun `taint facts speak the canonical vocabulary`() {
        assertEquals(VulnTypeId("cmdi"), assertNotNull(PhpStubs.function("exec")).sinkFacts.single().vulnType)
        assertEquals(VulnTypeId("sqli"), assertNotNull(PhpStubs.method("mysqli::query")).sinkFacts.single().vulnType)
        val filterVar = assertNotNull(PhpStubs.function("filter_var"))
        assertEquals(5, filterVar.sanitizerFacts.size)
        assertTrue(filterVar.sanitizerFacts.all { it.condition != null && it.vulnTypes == setOf(VulnTypeId("xss")) })
    }

    @Test
    fun `taint rules outrank taint for the same key`() {
        val readfile = assertNotNull(PhpStubs.function("readfile"))
        assertEquals(
            setOf(VulnType.XSS.id, VulnType.SSRF.id, VulnType.PATHTRAV.id, VulnType.DESER.id),
            readfile.sinkFacts.map { it.vulnType }.toSet(),
        )
        assertTrue(readfile.sinkFacts.all { it.condition == null && it.port == Port.Argument(0) })
    }

    @Test
    fun `a lookup over the same mounts holds equal records`() {
        val extended = PhpStubs.with("/consumer-test/")
        assertEquals(PhpStubs.function("substr"), extended.function("substr"))
        assertEquals(PhpStubs.method("mysqli::query"), extended.method("mysqli::query"))
        assertEquals(extended.function("consumer_only"), PhpStubs.with("/consumer-test/").function("consumer_only"))
    }

    @Test
    fun `with mounts a classpath consumer set after the bundled ones`() {
        val extended = PhpStubs.with("/consumer-test/")
        val added = assertNotNull(extended.function("consumer_only"))
        assertNull(added.extension)
        assertNotNull(added.callableSignature)
        assertEquals(VulnTypeId("sqli"), added.sinkFacts.single().vulnType)
        assertEquals("core", extended.function("strlen")!!.extension)
        assertNull(PhpStubs.function("consumer_only"))
        assertEquals(
            ReturnKind.NUM,
            PhpStubs
                .function("strlen")!!
                .returns
                .single()
                .kind,
        )
    }

    @Test
    fun `a consumer set without provenance mounts as manual`() {
        val extended = PhpStubs.with("/consumer-test/")
        assertEquals(ReturnKind.STR, assertNotNull(extended.function("strlen")).returns.single().kind)
    }

    @Test
    fun `a consumer set with generated provenance loses to a bundled manual entry`() {
        val extended = PhpStubs.with("/consumer-generated/")
        assertEquals(ReturnKind.NUM, assertNotNull(extended.function("strlen")).returns.single().kind)
        assertNull(assertNotNull(extended.function("extension_generated_only")).extension)
    }

    @Test
    fun `later consumer roots override earlier ones`() {
        val forward = PhpStubs.with("/consumer-test/", "/consumer-second/")
        assertEquals(ReturnKind.ANY, assertNotNull(forward.function("strlen")).returns.single().kind)
        val reverse = PhpStubs.with("/consumer-second/", "/consumer-test/")
        assertEquals(ReturnKind.STR, assertNotNull(reverse.function("strlen")).returns.single().kind)
    }

    @Test
    fun `plus chains like with`() {
        val chained = PhpStubs + "/consumer-test/" + "/consumer-second/"
        val together = PhpStubs.with("/consumer-test/", "/consumer-second/")
        assertEquals(together.function("strlen"), chained.function("strlen"))
        assertEquals(together.function("consumer_only"), chained.function("consumer_only"))
        assertEquals(together.function("consumer_only"), (PhpStubs + "/consumer-test/").function("consumer_only"))
    }

    @Test
    fun `with mounts a directory consumer set`(
        @TempDir dir: Path,
    ) {
        Files.writeString(dir.resolve("index.txt"), "dir.yaml\n")
        Files.writeString(dir.resolve("dir.yaml"), "- subject: {function: directory_only}\n  returns: str\n")
        assertEquals(ReturnKind.STR, assertNotNull((PhpStubs + dir).function("directory_only")).returns.single().kind)
        assertNotNull(PhpStubs.with(dir).function("directory_only"))
    }

    @Test
    fun `a consumer set failure surfaces from the mounting call`(
        @TempDir dir: Path,
    ) {
        assertTrue(assertFailsWith<StubIndexNotFoundException> { PhpStubs.with(dir) }.message!!.endsWith("$dir/index.txt"))
        val absent = assertFailsWith<StubIndexNotFoundException> { PhpStubs.with("/absent-root/") }
        assertTrue(absent.message!!.endsWith("/absent-root/index.txt"))
        assertNotNull(assertFailsWith<StubIndexInvalidException> { PhpStubs.with("/models-invalid/") }.cause)
    }

    @Test
    fun `a directory consumer set names the absent document`(
        @TempDir dir: Path,
    ) {
        Files.writeString(dir.resolve("index.txt"), "absent.yaml\n")
        val failure = assertFailsWith<StubIndexNotFoundException> { PhpStubs.with(dir) }
        assertTrue(failure.message!!.endsWith("$dir/absent.yaml"))
    }
}
