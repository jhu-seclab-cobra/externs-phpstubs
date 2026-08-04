package edu.jhu.cobra.externs.phpstubs

import java.io.BufferedReader
import java.io.StringReader
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for [YamlStubParser].
 *
 * - `parse function with all fields` -- full function entry round-trips correctly.
 * - `parse function with flowsToReturn` -- flowsToReturn set populated.
 * - `parse function minimal` -- defaults applied when only name is provided.
 * - `parse method with class and visibility` -- method fields including owningClass.
 * - `parse class with parent and interfaces` -- class inheritance fields.
 * - `parse constant with type and value` -- constant record fields.
 * - `parse class_constant` -- class constant with owningClass.
 * - `parse property` -- property record with owningClass and visibility.
 * - `parse method minimal` -- method with only required fields.
 * - `parse class minimal` -- class with only name.
 * - `parse class_constant minimal` -- class constant without visibility.
 * - `parse property minimal` -- property with only required fields.
 * - `unknown tag throws StubIndexInvalidException` -- rejects invalid tags.
 * - `missing name throws StubIndexInvalidException` -- rejects entry without name.
 * - `missing constant type throws StubIndexInvalidException` -- rejects constant without type.
 * - `missing constant value throws StubIndexInvalidException` -- rejects constant without value.
 * - `missing class_constant type throws StubIndexInvalidException` -- rejects class_constant without type.
 * - `missing class_constant value throws StubIndexInvalidException` -- rejects class_constant without value.
 * - `missing class on class_constant throws StubIndexInvalidException` -- rejects class_constant without class.
 * - `missing class on property throws StubIndexInvalidException` -- rejects property without class.
 * - `missing tag field throws StubIndexInvalidException` -- rejects entry without tag.
 * - `missing class on method throws StubIndexInvalidException` -- rejects method without class.
 * - `non-list top-level throws StubIndexInvalidException` -- rejects non-list YAML.
 * - `non-map entry throws StubIndexInvalidException` -- rejects non-map list element.
 * - `mixed tags in single file parsed correctly` -- multiple tag types in one YAML.
 * - `union types mapped to MIXED` -- pipe-separated types resolve to MIXED.
 * - `union type in param mapped to MIXED` -- pipe in param type resolves to MIXED.
 * - `empty file returns empty ParseResult` -- null/empty YAML handled.
 * - `mapPhpType maps known types` -- all recognized type strings.
 * - `mapPhpType maps aliases` -- integer, double, boolean aliases.
 * - `mapPhpType throws on unknown type` -- unknown type strings rejected.
 * - `mapVisibility throws on unknown visibility` -- unknown visibility strings rejected.
 * - `mapVisibility defaults absent visibility to PUBLIC` -- null means absent field.
 * - `mapPhpType is case insensitive` -- case normalization.
 * - `constant with integer value parsed as string` -- SnakeYAML Integer to String.
 * - `param name on parsed as string not boolean` -- YAML special value preserved.
 * - `param name true parsed as string not boolean` -- YAML special value preserved.
 * - `flowsToReturn with empty list` -- empty flowsToReturn yields empty set.
 * - `extension passed through to all records` -- extension field propagation.
 * - `method with static true` -- static method parsing.
 * - `property with static true` -- static property parsing.
 * - `class with abstract true` -- abstract class parsing.
 * - `param with default infers optional` -- optional inferred from default presence.
 * - `parse error message is prefixed with source` -- entry errors name the YAML file.
 * - `non-list top-level error message is prefixed with source` -- top-level errors name the YAML file.
 * - `syntactically broken YAML throws StubIndexInvalidException naming source` -- snakeyaml errors wrapped.
 * - `method static string value throws StubIndexInvalidException` -- non-boolean 'static' rejected.
 * - `class abstract string value throws StubIndexInvalidException` -- non-boolean 'abstract' rejected.
 * - `param optional string value throws StubIndexInvalidException` -- non-boolean 'optional' rejected.
 * - `param non-optional with default throws StubIndexInvalidException` -- optional/default conflict
 *   reported as parse error naming the param.
 */
internal class YamlStubParserTest {
    private fun parseYaml(
        yaml: String,
        extension: String = "standard",
    ): YamlStubParser.ParseResult = YamlStubParser.parse(BufferedReader(StringReader(yaml)), SOURCE, extension)

    private companion object {
        const val SOURCE = "test.yaml"
    }

    @Test
    fun `parse function with all fields`() {
        val yaml =
            """
            - tag: function
              name: substr
              params:
                - name: string
                  type: string
                - name: offset
                  type: int
                - name: length
                  type: int
                  optional: true
                  default: "null"
              return: string
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.functions.size)
        val func = result.functions[0]
        assertEquals("substr", func.name)
        assertEquals("standard", func.extension)
        assertEquals(PhpType.STRING, func.returnType)
        assertEquals(3, func.params.size)
        assertEquals("string", func.params[0].name)
        assertEquals(PhpType.STRING, func.params[0].type)
        assertEquals(false, func.params[0].optional)
        assertEquals("offset", func.params[1].name)
        assertEquals(PhpType.INT, func.params[1].type)
        assertEquals("length", func.params[2].name)
        assertEquals(true, func.params[2].optional)
        assertEquals("null", func.params[2].defaultValue)
    }

    @Test
    fun `parse function with flowsToReturn`() {
        val yaml =
            """
            - tag: function
              name: str_replace
              params:
                - name: search
                  type: string
                - name: replace
                  type: string
                - name: subject
                  type: string
              return: string
              flowsToReturn:
                - 1
                - 2
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.functions.size)
        assertEquals(setOf(1, 2), result.functions[0].flowsToReturn)
    }

    @Test
    fun `parse function minimal`() {
        val yaml =
            """
            - tag: function
              name: phpinfo
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.functions.size)
        val func = result.functions[0]
        assertEquals("phpinfo", func.name)
        assertEquals(PhpType.MIXED, func.returnType)
        assertEquals(emptyList(), func.params)
        assertEquals(emptySet(), func.flowsToReturn)
    }

    @Test
    fun `parse method with class and visibility`() {
        val yaml =
            """
            - tag: method
              name: query
              class: PDO
              params:
                - name: statement
                  type: string
              return: object
              static: false
              visibility: public
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.methods.size)
        val method = result.methods[0]
        assertEquals("query", method.name)
        assertEquals("PDO", method.owningClass)
        assertEquals(PhpType.OBJECT, method.returnType)
        assertEquals(Visibility.PUBLIC, method.visibility)
        assertEquals(false, method.isStatic)
        assertEquals(1, method.params.size)
    }

    @Test
    fun `parse class with parent and interfaces`() {
        val yaml =
            """
            - tag: class
              name: PDOStatement
              parent: PDO
              interfaces:
                - Traversable
                - Countable
              abstract: false
              final: true
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.classes.size)
        val cls = result.classes[0]
        assertEquals("PDOStatement", cls.name)
        assertEquals("PDO", cls.parent)
        assertEquals(listOf("Traversable", "Countable"), cls.interfaces)
        assertEquals(false, cls.isAbstract)
        assertEquals(true, cls.isFinal)
    }

    @Test
    fun `parse constant with type and value`() {
        val yaml =
            """
            - tag: constant
              name: PHP_INT_MAX
              type: int
              value: 9223372036854775807
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.constants.size)
        val const = result.constants[0]
        assertEquals("PHP_INT_MAX", const.name)
        assertEquals(PhpType.INT, const.type)
        assertEquals("9223372036854775807", const.value)
    }

    @Test
    fun `parse class_constant`() {
        val yaml =
            """
            - tag: class_constant
              name: FETCH_ASSOC
              class: PDO
              type: int
              value: 2
              visibility: public
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.classConstants.size)
        val cc = result.classConstants[0]
        assertEquals("FETCH_ASSOC", cc.name)
        assertEquals("PDO", cc.owningClass)
        assertEquals(PhpType.INT, cc.type)
        assertEquals("2", cc.value)
        assertEquals(Visibility.PUBLIC, cc.visibility)
    }

    @Test
    fun `parse property`() {
        val yaml =
            """
            - tag: property
              name: errorCode
              class: PDO
              type: string
              static: false
              visibility: protected
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.properties.size)
        val prop = result.properties[0]
        assertEquals("errorCode", prop.name)
        assertEquals("PDO", prop.owningClass)
        assertEquals(PhpType.STRING, prop.type)
        assertEquals(false, prop.isStatic)
        assertEquals(Visibility.PROTECTED, prop.visibility)
    }

    @Test
    fun `parse error message is prefixed with source`() {
        val yaml =
            """
            - tag: banana
              name: x
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
        assertEquals("Stub index is invalid: $SOURCE: Unknown tag: banana", ex.message)
    }

    @Test
    fun `non-list top-level error message is prefixed with source`() {
        val yaml =
            """
            tag: function
            name: strlen
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
        assertEquals("Stub index is invalid: $SOURCE: Expected YAML list at top level", ex.message)
    }

    @Test
    fun `unknown tag throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: interface
              name: Serializable
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `missing name throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: function
              return: string
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `missing constant type throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: constant
              name: SOME_CONST
              value: 42
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `missing constant value throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: constant
              name: SOME_CONST
              type: int
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `missing tag field throws StubIndexInvalidException`() {
        val yaml =
            """
            - name: strlen
              return: int
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `missing class on method throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: method
              name: doSomething
              return: void
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `mixed tags in single file parsed correctly`() {
        val yaml =
            """
            - tag: function
              name: strlen
              return: int
            - tag: class
              name: DateTime
            - tag: method
              name: format
              class: DateTime
              return: string
            - tag: constant
              name: PHP_EOL
              type: string
              value: "\n"
            - tag: class_constant
              name: ATOM
              class: DateTime
              type: string
              value: "Y-m-d\\TH:i:sP"
            - tag: property
              name: date
              class: DateTime
              type: string
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.functions.size)
        assertEquals(1, result.classes.size)
        assertEquals(1, result.methods.size)
        assertEquals(1, result.constants.size)
        assertEquals(1, result.classConstants.size)
        assertEquals(1, result.properties.size)
    }

    @Test
    fun `union types mapped to MIXED`() {
        val yaml =
            """
            - tag: function
              name: array_pop
              return: "string|false"
            """.trimIndent()
        val result = parseYaml(yaml)
        assertEquals(PhpType.MIXED, result.functions[0].returnType)
    }

    @Test
    fun `empty file returns empty ParseResult`() {
        val result = parseYaml("")
        assertTrue(result.functions.isEmpty())
        assertTrue(result.classes.isEmpty())
        assertTrue(result.methods.isEmpty())
        assertTrue(result.constants.isEmpty())
        assertTrue(result.classConstants.isEmpty())
        assertTrue(result.properties.isEmpty())
    }

    @Test
    fun `mapPhpType maps known types`() {
        assertEquals(PhpType.STRING, YamlStubParser.mapPhpType("string", SOURCE))
        assertEquals(PhpType.INT, YamlStubParser.mapPhpType("int", SOURCE))
        assertEquals(PhpType.INT, YamlStubParser.mapPhpType("integer", SOURCE))
        assertEquals(PhpType.FLOAT, YamlStubParser.mapPhpType("float", SOURCE))
        assertEquals(PhpType.FLOAT, YamlStubParser.mapPhpType("double", SOURCE))
        assertEquals(PhpType.BOOL, YamlStubParser.mapPhpType("bool", SOURCE))
        assertEquals(PhpType.BOOL, YamlStubParser.mapPhpType("boolean", SOURCE))
        assertEquals(PhpType.ARRAY, YamlStubParser.mapPhpType("array", SOURCE))
        assertEquals(PhpType.OBJECT, YamlStubParser.mapPhpType("object", SOURCE))
        assertEquals(PhpType.MIXED, YamlStubParser.mapPhpType("mixed", SOURCE))
        assertEquals(PhpType.VOID, YamlStubParser.mapPhpType("void", SOURCE))
        assertEquals(PhpType.NULL, YamlStubParser.mapPhpType("null", SOURCE))
        assertEquals(PhpType.CALLABLE, YamlStubParser.mapPhpType("callable", SOURCE))
        assertEquals(PhpType.RESOURCE, YamlStubParser.mapPhpType("resource", SOURCE))
    }

    @Test
    fun `mapPhpType throws on unknown type`() {
        assertFailsWith<StubIndexInvalidException> { YamlStubParser.mapPhpType("SomeClass", SOURCE) }
        assertFailsWith<StubIndexInvalidException> { YamlStubParser.mapPhpType("iterable", SOURCE) }
    }

    @Test
    fun `mapVisibility throws on unknown visibility`() {
        assertFailsWith<StubIndexInvalidException> { YamlStubParser.mapVisibility("banana", SOURCE) }
    }

    @Test
    fun `mapVisibility defaults absent visibility to PUBLIC`() {
        assertEquals(Visibility.PUBLIC, YamlStubParser.mapVisibility(null, SOURCE))
    }

    @Test
    fun `mapPhpType is case insensitive`() {
        assertEquals(PhpType.STRING, YamlStubParser.mapPhpType("String", SOURCE))
        assertEquals(PhpType.INT, YamlStubParser.mapPhpType("INT", SOURCE))
        assertEquals(PhpType.BOOL, YamlStubParser.mapPhpType("Boolean", SOURCE))
    }

    // -- Additional tag coverage: minimal fields --

    @Test
    fun `parse method minimal`() {
        val yaml =
            """
            - tag: method
              name: doSomething
              class: MyClass
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.methods.size)
        val method = result.methods[0]
        assertEquals("doSomething", method.name)
        assertEquals("MyClass", method.owningClass)
        assertEquals(PhpType.MIXED, method.returnType)
        assertEquals(emptyList<StubParam>(), method.params)
        assertEquals(false, method.isStatic)
        assertEquals(Visibility.PUBLIC, method.visibility)
    }

    @Test
    fun `parse class minimal`() {
        val yaml =
            """
            - tag: class
              name: stdClass
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.classes.size)
        val cls = result.classes[0]
        assertEquals("stdClass", cls.name)
        assertEquals(null, cls.parent)
        assertEquals(emptyList(), cls.interfaces)
        assertEquals(false, cls.isAbstract)
        assertEquals(false, cls.isFinal)
    }

    @Test
    fun `parse class_constant minimal`() {
        val yaml =
            """
            - tag: class_constant
              name: MY_CONST
              class: MyClass
              type: int
              value: 42
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.classConstants.size)
        val cc = result.classConstants[0]
        assertEquals(Visibility.PUBLIC, cc.visibility)
    }

    @Test
    fun `parse property minimal`() {
        val yaml =
            """
            - tag: property
              name: data
              class: MyClass
            """.trimIndent()

        val result = parseYaml(yaml)
        assertEquals(1, result.properties.size)
        val prop = result.properties[0]
        assertEquals("data", prop.name)
        assertEquals("MyClass", prop.owningClass)
        assertEquals(PhpType.MIXED, prop.type)
        assertEquals(false, prop.isStatic)
        assertEquals(Visibility.PUBLIC, prop.visibility)
    }

    // -- Additional error cases --

    @Test
    fun `missing class_constant type throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: class_constant
              name: X
              class: Foo
              value: 1
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `missing class_constant value throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: class_constant
              name: X
              class: Foo
              type: int
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `missing class on class_constant throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: class_constant
              name: X
              type: int
              value: 1
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `missing class on property throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: property
              name: data
              type: string
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `non-list top-level throws StubIndexInvalidException`() {
        val yaml =
            """
            tag: function
            name: strlen
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    @Test
    fun `non-map entry throws StubIndexInvalidException`() {
        val yaml =
            """
            - just a string
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
    }

    // -- Union types and type mapping --

    @Test
    fun `union type in param mapped to MIXED`() {
        val yaml =
            """
            - tag: function
              name: test
              params:
                - name: value
                  type: "string|array"
            """.trimIndent()
        val result = parseYaml(yaml)
        assertEquals(PhpType.MIXED, result.functions[0].params[0].type)
    }

    @Test
    fun `mapPhpType maps aliases`() {
        assertEquals(PhpType.INT, YamlStubParser.mapPhpType("integer", SOURCE))
        assertEquals(PhpType.FLOAT, YamlStubParser.mapPhpType("double", SOURCE))
        assertEquals(PhpType.BOOL, YamlStubParser.mapPhpType("boolean", SOURCE))
    }

    // -- SnakeYAML edge cases --

    @Test
    fun `constant with integer value parsed as string`() {
        val yaml =
            """
            - tag: constant
              name: MY_CONST
              type: int
              value: 42
            """.trimIndent()
        val result = parseYaml(yaml)
        assertEquals("42", result.constants[0].value)
    }

    @Test
    fun `param name on parsed as string not boolean`() {
        val yaml =
            """
            - tag: function
              name: test
              params:
                - name: "on"
                  type: bool
            """.trimIndent()
        val result = parseYaml(yaml)
        assertEquals("on", result.functions[0].params[0].name)
    }

    @Test
    fun `param name true parsed as string not boolean`() {
        val yaml =
            """
            - tag: function
              name: test
              params:
                - name: "true"
                  type: bool
            """.trimIndent()
        val result = parseYaml(yaml)
        assertEquals("true", result.functions[0].params[0].name)
    }

    @Test
    fun `flowsToReturn with empty list`() {
        val yaml =
            """
            - tag: function
              name: test
              flowsToReturn: []
            """.trimIndent()
        val result = parseYaml(yaml)
        assertEquals(emptySet(), result.functions[0].flowsToReturn)
    }

    @Test
    fun `extension passed through to all records`() {
        val yaml =
            """
            - tag: function
              name: f
            - tag: class
              name: C
            - tag: method
              name: m
              class: C
            - tag: constant
              name: K
              type: int
              value: 1
            - tag: class_constant
              name: CC
              class: C
              type: int
              value: 2
            - tag: property
              name: p
              class: C
            """.trimIndent()
        val result = parseYaml(yaml, "myext")
        assertEquals("myext", result.functions[0].extension)
        assertEquals("myext", result.classes[0].extension)
        assertEquals("myext", result.methods[0].extension)
        assertEquals("myext", result.constants[0].extension)
        assertEquals("myext", result.classConstants[0].extension)
        assertEquals("myext", result.properties[0].extension)
    }

    @Test
    fun `method with static true`() {
        val yaml =
            """
            - tag: method
              name: create
              class: Factory
              static: true
            """.trimIndent()
        val result = parseYaml(yaml)
        assertTrue(result.methods[0].isStatic)
    }

    @Test
    fun `property with static true`() {
        val yaml =
            """
            - tag: property
              name: instance
              class: Singleton
              static: true
            """.trimIndent()
        val result = parseYaml(yaml)
        assertTrue(result.properties[0].isStatic)
    }

    @Test
    fun `class with abstract true`() {
        val yaml =
            """
            - tag: class
              name: AbstractBase
              abstract: true
            """.trimIndent()
        val result = parseYaml(yaml)
        assertTrue(result.classes[0].isAbstract)
    }

    @Test
    fun `syntactically broken YAML throws StubIndexInvalidException naming source`() {
        val yaml =
            """
            - tag: function
              name: [unclosed
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
        val message = assertNotNull(ex.message)
        assertTrue(SOURCE in message, "expected message to name $SOURCE, was: $message")
    }

    @Test
    fun `method static string value throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: method
              name: create
              class: Factory
              static: "true"
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
        val message = assertNotNull(ex.message)
        assertTrue("static" in message, "expected message to name field 'static', was: $message")
    }

    @Test
    fun `class abstract string value throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: class
              name: AbstractBase
              abstract: "yes"
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
        val message = assertNotNull(ex.message)
        assertTrue("abstract" in message, "expected message to name field 'abstract', was: $message")
    }

    @Test
    fun `param optional string value throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: function
              name: test
              params:
                - name: x
                  type: int
                  optional: "true"
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
        val message = assertNotNull(ex.message)
        assertTrue("optional" in message, "expected message to name field 'optional', was: $message")
    }

    @Test
    fun `param non-optional with default throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: function
              name: test
              params:
                - name: x
                  type: int
                  optional: false
                  default: "10"
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseYaml(yaml) }
        val message = assertNotNull(ex.message)
        assertTrue("x" in message, "expected message to name param 'x', was: $message")
        assertTrue(SOURCE in message, "expected message to name $SOURCE, was: $message")
    }

    @Test
    fun `param with default infers optional`() {
        val yaml =
            """
            - tag: function
              name: test
              params:
                - name: x
                  type: int
                  default: "10"
            """.trimIndent()
        val result = parseYaml(yaml)
        val param = result.functions[0].params[0]
        assertTrue(param.optional)
        assertEquals("10", param.defaultValue)
    }
}
