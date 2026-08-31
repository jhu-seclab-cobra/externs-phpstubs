package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * Tests for [YamlStubParser] — `class`, `constant`, `class_constant`, and `property` entries,
 * mixed-tag files, extension propagation, and SnakeYAML value edge cases.
 *
 * - `parse class with parent and interfaces` -- class inheritance fields.
 * - `parse class minimal` -- class with only name.
 * - `class with abstract true` -- abstract class parsing.
 * - `parse constant with type and value` -- constant record fields.
 * - `constant with integer value parsed as string` -- SnakeYAML Integer to String.
 * - `parse class_constant` -- class constant with owningClass.
 * - `parse class_constant minimal` -- class constant without visibility.
 * - `parse property` -- property record with owningClass and visibility.
 * - `parse property minimal` -- property with only required fields.
 * - `property with static true` -- static property parsing.
 * - `mixed tags in single file parsed correctly` -- multiple tag types in one YAML.
 * - `extension passed through to all records` -- extension field propagation.
 * - `empty file returns empty ParseResult` -- null/empty YAML handled.
 */
internal class YamlStubParserClassTest {
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

        val result = parseStubYaml(yaml)
        assertEquals(1, result.classes.size)
        val cls = result.classes[0]
        assertEquals("PDOStatement", cls.name)
        assertEquals("PDO", cls.parent)
        assertEquals(listOf("Traversable", "Countable"), cls.interfaces)
        assertEquals(false, cls.isAbstract)
        assertEquals(true, cls.isFinal)
    }

    @Test
    fun `parse class minimal`() {
        val yaml =
            """
            - tag: class
              name: stdClass
            """.trimIndent()

        val result = parseStubYaml(yaml)
        assertEquals(1, result.classes.size)
        val cls = result.classes[0]
        assertEquals("stdClass", cls.name)
        assertEquals(null, cls.parent)
        assertEquals(emptyList(), cls.interfaces)
        assertEquals(false, cls.isAbstract)
        assertEquals(false, cls.isFinal)
    }

    @Test
    fun `class with abstract true`() {
        val yaml =
            """
            - tag: class
              name: AbstractBase
              abstract: true
            """.trimIndent()
        val result = parseStubYaml(yaml)
        assertTrue(result.classes[0].isAbstract)
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

        val result = parseStubYaml(yaml)
        assertEquals(1, result.constants.size)
        val const = result.constants[0]
        assertEquals("PHP_INT_MAX", const.name)
        assertEquals(PhpType.INT, const.type)
        assertEquals("9223372036854775807", const.value)
    }

    @Test
    fun `constant with integer value parsed as string`() {
        val yaml =
            """
            - tag: constant
              name: MY_CONST
              type: int
              value: 42
            """.trimIndent()
        val result = parseStubYaml(yaml)
        assertEquals("42", result.constants[0].value)
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

        val result = parseStubYaml(yaml)
        assertEquals(1, result.classConstants.size)
        val cc = result.classConstants[0]
        assertEquals("FETCH_ASSOC", cc.name)
        assertEquals("PDO", cc.owningClass)
        assertEquals(PhpType.INT, cc.type)
        assertEquals("2", cc.value)
        assertEquals(Visibility.PUBLIC, cc.visibility)
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

        val result = parseStubYaml(yaml)
        assertEquals(1, result.classConstants.size)
        val cc = result.classConstants[0]
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

        val result = parseStubYaml(yaml)
        assertEquals(1, result.properties.size)
        val prop = result.properties[0]
        assertEquals("errorCode", prop.name)
        assertEquals("PDO", prop.owningClass)
        assertEquals(PhpType.STRING, prop.type)
        assertEquals(false, prop.isStatic)
        assertEquals(Visibility.PROTECTED, prop.visibility)
    }

    @Test
    fun `parse property minimal`() {
        val yaml =
            """
            - tag: property
              name: data
              class: MyClass
            """.trimIndent()

        val result = parseStubYaml(yaml)
        assertEquals(1, result.properties.size)
        val prop = result.properties[0]
        assertEquals("data", prop.name)
        assertEquals("MyClass", prop.owningClass)
        assertEquals(PhpType.MIXED, prop.type)
        assertEquals(false, prop.isStatic)
        assertEquals(Visibility.PUBLIC, prop.visibility)
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
        val result = parseStubYaml(yaml)
        assertTrue(result.properties[0].isStatic)
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

        val result = parseStubYaml(yaml)
        assertEquals(1, result.functions.size)
        assertEquals(1, result.classes.size)
        assertEquals(1, result.methods.size)
        assertEquals(1, result.constants.size)
        assertEquals(1, result.classConstants.size)
        assertEquals(1, result.properties.size)
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
        val result = parseStubYaml(yaml, "myext")
        assertEquals("myext", result.functions[0].extension)
        assertEquals("myext", result.classes[0].extension)
        assertEquals("myext", result.methods[0].extension)
        assertEquals("myext", result.constants[0].extension)
        assertEquals("myext", result.classConstants[0].extension)
        assertEquals("myext", result.properties[0].extension)
    }

    @Test
    fun `empty file returns empty ParseResult`() {
        val result = parseStubYaml("")
        assertTrue(result.functions.isEmpty())
        assertTrue(result.classes.isEmpty())
        assertTrue(result.methods.isEmpty())
        assertTrue(result.constants.isEmpty())
        assertTrue(result.classConstants.isEmpty())
        assertTrue(result.properties.isEmpty())
    }
}
