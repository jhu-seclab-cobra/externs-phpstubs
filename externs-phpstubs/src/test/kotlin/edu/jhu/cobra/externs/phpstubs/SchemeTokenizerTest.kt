package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.TokenizerLanguage
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for the tokenizer language the canonical vocabulary declares for scheme injection.
 *
 * - `only scheme injection declares a tokenizer` — verifies no other vulnerability type and no source kind holds one
 * - `a value lands at URL start inside a URL attribute value` — verifies the target states over HTML texts
 * - `a position that is not URL start is not a target` — verifies text, comments, other attributes and fixed schemes
 * - `a comment reads as HTML does` — verifies the comment forms that end early
 * - `a closed tag returns to the text state` — verifies the start state, the six targets and the return to text
 */
internal class SchemeTokenizerTest {
    private val language: TokenizerLanguage =
        assertNotNull(PhpStubs.vocabulary.vulnTypes.getValue(VulnType.SCHEMEI.id).tokenizer)

    private fun atUrlStart(text: String): Boolean = language.run(language.start, text) in language.targets

    @Test
    fun `only scheme injection declares a tokenizer`() {
        for (type in VulnType.entries - VulnType.SCHEMEI) {
            assertNull(PhpStubs.vocabulary.vulnTypes.getValue(type.id).tokenizer, type.id.id)
        }
    }

    @Test
    fun `a value lands at URL start inside a URL attribute value`() {
        val texts =
            listOf(
                """<a href=""",
                """<a href=""" + "\"",
                """<a href='""",
                """<a href = "  """,
                """<A HREF="""",
                """<a class="x" href="""",
                """<a title="x"href="""",
                """<a data-x href="""",
                """<img src="""",
                """<form action="""",
                """<button formaction="""",
                """<svg><a xlink:href="""",
                """<a href=" """,
                "<a href=\"\t\n",
                """<a href="java""",
                """<a href='java""",
                """<a href=java""",
                """<p>text</p><a href="""",
                """<!-- --> <a href="""",
                """<!-- a --!> <a href="""",
                """<!--> <a href="""",
                """<!---> <a href="""",
                """<!-- a -- b --> <a href="""",
                """<a/href="""",
            )
        for (text in texts) {
            assertTrue(atUrlStart(text), text)
        }
    }

    @Test
    fun `a position that is not URL start is not a target`() {
        val texts =
            listOf(
                "",
                "plain text",
                "<p>",
                "<p",
                "<",
                "< a href=\"",
                """<a title="href=""",
                """<a title=href=""",
                """<a data-href="""",
                """<a hrefs="""",
                """<a xhref="""",
                """<a href="index.php?id=""",
                """<a href="x:""",
                """<a href="/""",
                """<a href="#""",
                """<a href="1""",
                """<a href="http://x/""",
                """<a href='/home/""",
                """<a href=/home/""",
                """<a href=x:""",
                """<a href="x" title="""",
                """<a href="x" """,
                """<a href="x">""",
                """<!-- <a href="""",
                """<!DOCTYPE html""",
                """<?php <a href="""",
                """</a href="""",
            )
        for (text in texts) {
            assertFalse(atUrlStart(text), text)
        }
    }

    @Test
    fun `a comment reads as HTML does`() {
        assertFalse(atUrlStart("""<!-- <a href="-->x <a href="x:"""))
        assertTrue(atUrlStart("""<!-- <a href="--> <a href=""""))
        assertTrue(atUrlStart("""<!-- <a href="--!> <a href=""""))
        assertFalse(atUrlStart("""<!-- <a href="--!"""))
        assertTrue(atUrlStart("""<!-- x --!> <a href=""""))
        assertFalse(atUrlStart("""<!-- x --! <a href=""""))
        assertTrue(atUrlStart("""<!x> <a href=""""))
        assertFalse(atUrlStart("""<!x <a href=""""))
    }

    @Test
    fun `a closed tag returns to the text state`() {
        assertEquals("text", language.start.name)
        assertEquals(6, language.targets.size)
        assertEquals(language.start, language.run(language.start, "<a href=\"x\">"))
    }
}
