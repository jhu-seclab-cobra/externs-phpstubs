package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for [YamlStubParser] — rejected inputs and error message contracts.
 *
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
 * - `parse error message is prefixed with source` -- entry errors name the YAML file.
 * - `non-list top-level error message is prefixed with source` -- top-level errors name the YAML file.
 * - `syntactically broken YAML throws StubIndexInvalidException naming source` -- snakeyaml errors wrapped.
 * - `method static string value throws StubIndexInvalidException` -- non-boolean 'static' rejected.
 * - `class abstract string value throws StubIndexInvalidException` -- non-boolean 'abstract' rejected.
 * - `param optional string value throws StubIndexInvalidException` -- non-boolean 'optional' rejected.
 * - `param non-optional with default throws StubIndexInvalidException` -- optional/default conflict
 *   reported as parse error naming the param.
 * - `flowsToReturn non-integer value throws StubIndexInvalidException` -- non-integer indices rejected.
 * - `params non-list value throws StubIndexInvalidException` -- scalar 'params' rejected.
 * - `interfaces non-list value throws StubIndexInvalidException` -- scalar 'interfaces' rejected.
 */
internal class YamlStubParserValidationTest {
    @Test
    fun `unknown tag throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: interface
              name: Serializable
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `missing name throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: function
              return: string
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `missing constant type throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: constant
              name: SOME_CONST
              value: 42
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `missing constant value throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: constant
              name: SOME_CONST
              type: int
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `missing class_constant type throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: class_constant
              name: X
              class: Foo
              value: 1
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
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
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
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
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `missing class on property throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: property
              name: data
              type: string
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `missing tag field throws StubIndexInvalidException`() {
        val yaml =
            """
            - name: strlen
              return: int
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `missing class on method throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: method
              name: doSomething
              return: void
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `non-list top-level throws StubIndexInvalidException`() {
        val yaml =
            """
            tag: function
            name: strlen
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `non-map entry throws StubIndexInvalidException`() {
        val yaml =
            """
            - just a string
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `parse error message is prefixed with source`() {
        val yaml =
            """
            - tag: banana
              name: x
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
        assertEquals("Stub index is invalid: $STUB_YAML_SOURCE: Unknown tag: banana", ex.message)
    }

    @Test
    fun `non-list top-level error message is prefixed with source`() {
        val yaml =
            """
            tag: function
            name: strlen
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
        assertEquals("Stub index is invalid: $STUB_YAML_SOURCE: Expected YAML list at top level", ex.message)
    }

    @Test
    fun `syntactically broken YAML throws StubIndexInvalidException naming source`() {
        val yaml =
            """
            - tag: function
              name: [unclosed
            """.trimIndent()
        val ex = assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
        val message = assertNotNull(ex.message)
        assertTrue(STUB_YAML_SOURCE in message, "expected message to name $STUB_YAML_SOURCE, was: $message")
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
        val ex = assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
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
        val ex = assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
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
        val ex = assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
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
        val ex = assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
        val message = assertNotNull(ex.message)
        assertTrue("x" in message, "expected message to name param 'x', was: $message")
        assertTrue(STUB_YAML_SOURCE in message, "expected message to name $STUB_YAML_SOURCE, was: $message")
    }

    @Test
    fun `flowsToReturn non-integer value throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: function
              name: test
              flowsToReturn:
                - one
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `params non-list value throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: function
              name: test
              params: notalist
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }

    @Test
    fun `interfaces non-list value throws StubIndexInvalidException`() {
        val yaml =
            """
            - tag: class
              name: ArrayObject
              interfaces: Traversable
            """.trimIndent()
        assertFailsWith<StubIndexInvalidException> { parseStubYaml(yaml) }
    }
}
