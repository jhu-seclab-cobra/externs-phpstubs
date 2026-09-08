package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.OriginId
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import edu.jhu.cobra.commons.phpmodels.VulnClassId
import org.junit.jupiter.api.io.TempDir
import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertSame
import kotlin.test.assertTrue

/**
 * Tests for the [PhpStubs] lookup over the bundled merge: exact lookups, enumerations, and extension sets.
 * Constant lookups: [PhpStubsConstantTest].
 *
 * - `function lookup folds case and the leading slash` — verifies the spelling is the format library's
 * - `function lookup misses an unknown name and rejects a member spelling` — verifies absence and argument error
 * - `keyword constructs and scalar classes are records` — verifies the language documents load
 * - `a record carries extension, signature, and the value unit in force` — verifies the manual rule outranks
 * - `method lookup accepts both spellings and needs the owner` — verifies the two method forms
 * - `record answers an already built subject` — verifies the subject-keyed lookup
 * - `predefined variables are records with source facts` — verifies the mapped taint sources
 * - `taint facts speak the canonical vocabulary` — verifies sinks, sanitizers, and conditions after mapping
 * - `enumerations cover every kind in first-statement order` — verifies the collections and fact lists
 * - `the vocabulary declares exactly the enum constants` — verifies VulnClass and Origin against the data
 * - `with mounts a classpath extension set after the bundled ones` — verifies override and addition
 * - `with mounts a directory extension set` — verifies the filesystem opener
 * - `an extension set failure surfaces from the mounting call` — verifies error classification
 */
internal class PhpStubsTest {
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
    fun `keyword constructs and scalar classes are records`() {
        for (name in listOf("echo", "isset", "require_once", "instanceof")) {
            assertEquals("keyword", assertNotNull(PhpStubs.function(name), name).extension)
        }
        for (name in listOf("int", "float", "string", "bool", "array")) {
            assertEquals("scalar", assertNotNull(PhpStubs.clazz(name), name).extension)
        }
        assertEquals("keyword", assertNotNull(PhpStubs.clazz("exit")).extension)
        assertNotNull(PhpStubs.clazz("resource"))
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
    fun `method lookup accepts both spellings and needs the owner`() {
        val record = assertNotNull(PhpStubs.method("Exception::getCode"))
        assertSame(record, PhpStubs.method("exception", "getcode"))
        assertEquals("int", record.callableSignature!!.returnType.toString())
        assertNull(PhpStubs.method("ArrayObject::getCode"))
        assertFailsWith<IllegalArgumentException> { PhpStubs.method("getCode") }
    }

    @Test
    fun `record answers an already built subject`() {
        assertSame(PhpStubs.function("substr"), PhpStubs.record(FunctionSubject("substr")))
        assertSame(PhpStubs.method("mysqli::query"), PhpStubs.record(MethodSubject("mysqli", "query")))
        assertNull(PhpStubs.record(FunctionSubject("nonexistent_function_xyz")))
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
    fun `taint facts speak the canonical vocabulary`() {
        assertEquals(VulnClassId("cmdi"), assertNotNull(PhpStubs.function("exec")).sinks.single().vulnClass)
        assertEquals(VulnClassId("sqli"), assertNotNull(PhpStubs.method("mysqli::query")).sinks.single().vulnClass)
        val filterVar = assertNotNull(PhpStubs.function("filter_var"))
        assertEquals(5, filterVar.sanitizers.size)
        assertTrue(filterVar.sanitizers.all { it.condition != null && it.categories == setOf(VulnClassId("xss")) })
        assertTrue(PhpStubs.sinks.none { it.vulnClass.id in setOf("sql", "html", "shell") })
    }

    @Test
    fun `enumerations cover every kind in first-statement order`() {
        assertTrue(PhpStubs.functions.size > 5000)
        assertTrue(PhpStubs.classes.isNotEmpty() && PhpStubs.methods.isNotEmpty() && PhpStubs.constants.isNotEmpty())
        assertTrue(PhpStubs.classConstants.isNotEmpty() && PhpStubs.variables.isNotEmpty())
        assertTrue(PhpStubs.sinks.isNotEmpty() && PhpStubs.sources.isNotEmpty() && PhpStubs.sanitizers.isNotEmpty())
        assertTrue(PhpStubs.flows.isNotEmpty() && PhpStubs.returns.isNotEmpty())
        assertEquals(
            PhpStubs.functions.first(),
            PhpStubs.function(
                PhpStubs.functions
                    .first()
                    .subject.name,
            ),
        )
        assertTrue(PhpStubs.policy.isDangerous(OriginId("user-input"), VulnClassId("xpathi")))
    }

    @Test
    fun `the vocabulary declares exactly the enum constants`() {
        assertEquals(VulnClass.entries.map { it.id }.toSet(), PhpStubs.vocabulary.vulnClasses.keys)
        assertEquals(Origin.entries.map { it.id }.toSet(), PhpStubs.vocabulary.origins.keys)
    }

    @Test
    fun `with mounts a classpath extension set after the bundled ones`() {
        val extended = PhpStubs.with("/extension-test/")
        val added = assertNotNull(extended.function("extension_only"))
        assertNull(added.extension)
        assertNotNull(added.callableSignature)
        assertEquals(VulnClassId("sqli"), added.sinks.single().vulnClass)
        assertEquals(ReturnKind.STR, assertNotNull(extended.function("strlen")).returns.single().kind)
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
        assertEquals(added, (PhpStubs + "/extension-test/").function("extension_only"))
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
        assertFailsWith<StubIndexInvalidException> { PhpStubs.with("/models-invalid/") }
    }
}
