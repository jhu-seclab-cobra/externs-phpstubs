package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

/**
 * Tests for [YamlStubParser] — type string and visibility string mapping.
 *
 * - `mapPhpType maps known types` -- all recognized type strings.
 * - `mapPhpType maps aliases` -- integer, double, boolean aliases.
 * - `mapPhpType is case insensitive` -- case normalization.
 * - `mapPhpType throws on unknown type` -- unknown type strings rejected.
 * - `union types mapped to MIXED` -- pipe-separated types resolve to MIXED.
 * - `mapVisibility throws on unknown visibility` -- unknown visibility strings rejected.
 * - `mapVisibility defaults absent visibility to PUBLIC` -- null means absent field.
 * - `mapVisibility is case insensitive` -- visibility strings accepted in any case.
 */
internal class YamlStubParserMappingTest {
    @Test
    fun `mapPhpType maps known types`() {
        assertEquals(PhpType.STRING, YamlStubParser.mapPhpType("string", STUB_YAML_SOURCE))
        assertEquals(PhpType.INT, YamlStubParser.mapPhpType("int", STUB_YAML_SOURCE))
        assertEquals(PhpType.INT, YamlStubParser.mapPhpType("integer", STUB_YAML_SOURCE))
        assertEquals(PhpType.FLOAT, YamlStubParser.mapPhpType("float", STUB_YAML_SOURCE))
        assertEquals(PhpType.FLOAT, YamlStubParser.mapPhpType("double", STUB_YAML_SOURCE))
        assertEquals(PhpType.BOOL, YamlStubParser.mapPhpType("bool", STUB_YAML_SOURCE))
        assertEquals(PhpType.BOOL, YamlStubParser.mapPhpType("boolean", STUB_YAML_SOURCE))
        assertEquals(PhpType.ARRAY, YamlStubParser.mapPhpType("array", STUB_YAML_SOURCE))
        assertEquals(PhpType.OBJECT, YamlStubParser.mapPhpType("object", STUB_YAML_SOURCE))
        assertEquals(PhpType.MIXED, YamlStubParser.mapPhpType("mixed", STUB_YAML_SOURCE))
        assertEquals(PhpType.VOID, YamlStubParser.mapPhpType("void", STUB_YAML_SOURCE))
        assertEquals(PhpType.NULL, YamlStubParser.mapPhpType("null", STUB_YAML_SOURCE))
        assertEquals(PhpType.CALLABLE, YamlStubParser.mapPhpType("callable", STUB_YAML_SOURCE))
        assertEquals(PhpType.RESOURCE, YamlStubParser.mapPhpType("resource", STUB_YAML_SOURCE))
    }

    @Test
    fun `mapPhpType maps aliases`() {
        assertEquals(PhpType.INT, YamlStubParser.mapPhpType("integer", STUB_YAML_SOURCE))
        assertEquals(PhpType.FLOAT, YamlStubParser.mapPhpType("double", STUB_YAML_SOURCE))
        assertEquals(PhpType.BOOL, YamlStubParser.mapPhpType("boolean", STUB_YAML_SOURCE))
    }

    @Test
    fun `mapPhpType is case insensitive`() {
        assertEquals(PhpType.STRING, YamlStubParser.mapPhpType("String", STUB_YAML_SOURCE))
        assertEquals(PhpType.INT, YamlStubParser.mapPhpType("INT", STUB_YAML_SOURCE))
        assertEquals(PhpType.BOOL, YamlStubParser.mapPhpType("Boolean", STUB_YAML_SOURCE))
    }

    @Test
    fun `mapPhpType throws on unknown type`() {
        assertFailsWith<StubIndexInvalidException> { YamlStubParser.mapPhpType("SomeClass", STUB_YAML_SOURCE) }
        assertFailsWith<StubIndexInvalidException> { YamlStubParser.mapPhpType("iterable", STUB_YAML_SOURCE) }
    }

    @Test
    fun `union types mapped to MIXED`() {
        val yaml =
            """
            - tag: function
              name: array_pop
              return: "string|false"
            """.trimIndent()
        val result = parseStubYaml(yaml)
        assertEquals(PhpType.MIXED, result.functions[0].returnType)
    }

    @Test
    fun `mapVisibility throws on unknown visibility`() {
        assertFailsWith<StubIndexInvalidException> { YamlStubParser.mapVisibility("banana", STUB_YAML_SOURCE) }
    }

    @Test
    fun `mapVisibility defaults absent visibility to PUBLIC`() {
        assertEquals(Visibility.PUBLIC, YamlStubParser.mapVisibility(null, STUB_YAML_SOURCE))
    }

    @Test
    fun `mapVisibility is case insensitive`() {
        assertEquals(Visibility.PUBLIC, YamlStubParser.mapVisibility("PUBLIC", STUB_YAML_SOURCE))
        assertEquals(Visibility.PROTECTED, YamlStubParser.mapVisibility("Protected", STUB_YAML_SOURCE))
        assertEquals(Visibility.PRIVATE, YamlStubParser.mapVisibility("PRIVATE", STUB_YAML_SOURCE))
    }
}
