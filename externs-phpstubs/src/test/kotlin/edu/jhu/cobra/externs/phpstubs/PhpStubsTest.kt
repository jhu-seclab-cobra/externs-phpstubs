package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.VulnClassId
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
 * Tests for [PhpStubs]: the bundled merge in Merge Order and the construction of extension merges through
 * [PhpStubs.with] and [PhpStubs.plus]. The read surface: [BuiltinLookupExactTest], [BuiltinLookupEnumerationTest].
 *
 * - `keyword constructs and scalar classes are records` — verifies the language documents load
 * - `a record carries extension, signature, and the value unit in force` — verifies the manual rule outranks
 * - `taint facts speak the canonical vocabulary` — verifies sinks, sanitizers, and conditions after mapping
 * - `taint rules outrank taint for the same key` — verifies the later manual set replaces the generated one
 * - `a lookup over the same mounts holds equal records` — verifies equal statements give equal records
 * - `with mounts a classpath extension set after the bundled ones` — verifies override and addition
 * - `an extension set without provenance mounts as manual` — verifies it replaces a bundled manual statement
 * - `an extension set with generated provenance loses to a bundled manual statement` — verifies rank over order
 * - `later extension roots override earlier ones` — verifies supplied order among extension sets
 * - `plus chains like with` — verifies the operator form
 * - `with mounts a directory extension set` — verifies the filesystem opener
 * - `an extension set failure surfaces from the mounting call` — verifies error classification
 * - `a directory extension set names the absent document` — verifies absence under the filesystem opener
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
        assertEquals("standard", strlen.extension)
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
    fun `taint facts speak the canonical vocabulary`() {
        assertEquals(VulnClassId("cmdi"), assertNotNull(PhpStubs.function("exec")).sinks.single().vulnClass)
        assertEquals(VulnClassId("sqli"), assertNotNull(PhpStubs.method("mysqli::query")).sinks.single().vulnClass)
        val filterVar = assertNotNull(PhpStubs.function("filter_var"))
        assertEquals(5, filterVar.sanitizers.size)
        assertTrue(filterVar.sanitizers.all { it.condition != null && it.categories == setOf(VulnClassId("xss")) })
    }

    @Test
    fun `taint rules outrank taint for the same key`() {
        val readfile = assertNotNull(PhpStubs.function("readfile"))
        assertEquals(
            setOf(VulnClass.XSS.id, VulnClass.SSRF.id, VulnClass.PATHTRAV.id, VulnClass.DESER.id),
            readfile.sinks.map { it.vulnClass }.toSet(),
        )
        assertTrue(readfile.sinks.all { it.condition == null && it.port == Port.Argument(0) })
    }

    @Test
    fun `a lookup over the same mounts holds equal records`() {
        val extended = PhpStubs.with("/extension-test/")
        assertEquals(PhpStubs.function("substr"), extended.function("substr"))
        assertEquals(PhpStubs.method("mysqli::query"), extended.method("mysqli::query"))
        assertEquals(extended.function("extension_only"), PhpStubs.with("/extension-test/").function("extension_only"))
    }

    @Test
    fun `with mounts a classpath extension set after the bundled ones`() {
        val extended = PhpStubs.with("/extension-test/")
        val added = assertNotNull(extended.function("extension_only"))
        assertNull(added.extension)
        assertNotNull(added.callableSignature)
        assertEquals(VulnClassId("sqli"), added.sinks.single().vulnClass)
        assertEquals("standard", extended.function("strlen")!!.extension)
        assertNull(PhpStubs.function("extension_only"))
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
    fun `an extension set without provenance mounts as manual`() {
        val extended = PhpStubs.with("/extension-test/")
        assertEquals(ReturnKind.STR, assertNotNull(extended.function("strlen")).returns.single().kind)
    }

    @Test
    fun `an extension set with generated provenance loses to a bundled manual statement`() {
        val extended = PhpStubs.with("/extension-generated/")
        assertEquals(ReturnKind.NUM, assertNotNull(extended.function("strlen")).returns.single().kind)
        assertNull(assertNotNull(extended.function("extension_generated_only")).extension)
    }

    @Test
    fun `later extension roots override earlier ones`() {
        val forward = PhpStubs.with("/extension-test/", "/extension-second/")
        assertEquals(ReturnKind.ANY, assertNotNull(forward.function("strlen")).returns.single().kind)
        val reverse = PhpStubs.with("/extension-second/", "/extension-test/")
        assertEquals(ReturnKind.STR, assertNotNull(reverse.function("strlen")).returns.single().kind)
    }

    @Test
    fun `plus chains like with`() {
        val chained = PhpStubs + "/extension-test/" + "/extension-second/"
        val together = PhpStubs.with("/extension-test/", "/extension-second/")
        assertEquals(together.function("strlen"), chained.function("strlen"))
        assertEquals(together.function("extension_only"), chained.function("extension_only"))
        assertEquals(together.function("extension_only"), (PhpStubs + "/extension-test/").function("extension_only"))
    }

    @Test
    fun `with mounts a directory extension set`(
        @TempDir dir: Path,
    ) {
        Files.writeString(dir.resolve("index.txt"), "dir.yaml\n")
        Files.writeString(dir.resolve("dir.yaml"), "- subject: {function: directory_only}\n  returns: str\n")
        assertEquals(ReturnKind.STR, assertNotNull((PhpStubs + dir).function("directory_only")).returns.single().kind)
        assertNotNull(PhpStubs.with(dir).function("directory_only"))
    }

    @Test
    fun `an extension set failure surfaces from the mounting call`(
        @TempDir dir: Path,
    ) {
        assertTrue(assertFailsWith<StubIndexNotFoundException> { PhpStubs.with(dir) }.message!!.endsWith("$dir/index.txt"))
        val absent = assertFailsWith<StubIndexNotFoundException> { PhpStubs.with("/absent-root/") }
        assertTrue(absent.message!!.endsWith("/absent-root/index.txt"))
        assertNotNull(assertFailsWith<StubIndexInvalidException> { PhpStubs.with("/models-invalid/") }.cause)
    }

    @Test
    fun `a directory extension set names the absent document`(
        @TempDir dir: Path,
    ) {
        Files.writeString(dir.resolve("index.txt"), "absent.yaml\n")
        val failure = assertFailsWith<StubIndexNotFoundException> { PhpStubs.with(dir) }
        assertTrue(failure.message!!.endsWith("$dir/absent.yaml"))
    }
}
