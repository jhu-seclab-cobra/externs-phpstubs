package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * Tests for [YamlStubParser] — `function` and `method` entries, params, and flowsToReturn.
 *
 * - `parse function with all fields` -- full function entry round-trips correctly.
 * - `parse function with flowsToReturn` -- flowsToReturn set populated.
 * - `parse function minimal` -- defaults applied when only name is provided.
 * - `flowsToReturn with empty list` -- empty flowsToReturn yields empty set.
 * - `union type in param mapped to MIXED` -- pipe in param type resolves to MIXED.
 * - `param with default infers optional` -- optional inferred from default presence.
 * - `param name on parsed as string not boolean` -- YAML special value preserved.
 * - `param name true parsed as string not boolean` -- YAML special value preserved.
 * - `parse method with class and visibility` -- method fields including owningClass.
 * - `parse method minimal` -- method with only required fields.
 * - `method with static true` -- static method parsing.
 */
internal class YamlStubParserFunctionTest {
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

        val result = parseStubYaml(yaml)
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

        val result = parseStubYaml(yaml)
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

        val result = parseStubYaml(yaml)
        assertEquals(1, result.functions.size)
        val func = result.functions[0]
        assertEquals("phpinfo", func.name)
        assertEquals(PhpType.MIXED, func.returnType)
        assertEquals(emptyList(), func.params)
        assertEquals(emptySet(), func.flowsToReturn)
    }

    @Test
    fun `flowsToReturn with empty list`() {
        val yaml =
            """
            - tag: function
              name: test
              flowsToReturn: []
            """.trimIndent()
        val result = parseStubYaml(yaml)
        assertEquals(emptySet(), result.functions[0].flowsToReturn)
    }

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
        val result = parseStubYaml(yaml)
        assertEquals(PhpType.MIXED, result.functions[0].params[0].type)
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
        val result = parseStubYaml(yaml)
        val param = result.functions[0].params[0]
        assertTrue(param.optional)
        assertEquals("10", param.defaultValue)
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
        val result = parseStubYaml(yaml)
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
        val result = parseStubYaml(yaml)
        assertEquals("true", result.functions[0].params[0].name)
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

        val result = parseStubYaml(yaml)
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
    fun `parse method minimal`() {
        val yaml =
            """
            - tag: method
              name: doSomething
              class: MyClass
            """.trimIndent()

        val result = parseStubYaml(yaml)
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
    fun `method with static true`() {
        val yaml =
            """
            - tag: method
              name: create
              class: Factory
              static: true
            """.trimIndent()
        val result = parseStubYaml(yaml)
        assertTrue(result.methods[0].isStatic)
    }
}
