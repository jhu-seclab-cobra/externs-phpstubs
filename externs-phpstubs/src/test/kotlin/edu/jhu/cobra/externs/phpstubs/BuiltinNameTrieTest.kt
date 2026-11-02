package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.Verification
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertSame
import kotlin.test.assertTrue

/**
 * Canonical query construction, full enumeration and actual per-cursor work.
 * - `trie and single name matching accept the same complete records` — shared transition semantics.
 * - `negative and complete queries charge every visited node and output` — explicit worst case and DFS memory.
 * - `existence stops at its first match without changing later full queries` — no persistent query cache.
 * - `effective merge indexes signatures before alias keys` — canonical subjects only, facts stay present.
 * - `independent effective merges do not share query results` — extension/override lifecycle.
 * - `bundled matches include an unloaded function without creating a second record` — real builtin intake.
 * - `query terminals use the effective signature and canonical namespace identity` — effective record lifecycle.
 */
internal class BuiltinNameTrieTest {
    private val names = listOf("strlen", "strpos", "substr", "system")

    private fun pattern(vararg parts: String?): NamePattern =
        NamePattern(
            parts.map { part ->
                if (part == null) NamePattern.Part.Gap else NamePattern.Part.Literal(part)
            },
        )

    private fun trie(): BuiltinNameTrie<FunctionSubject> =
        BuiltinNameTrie<FunctionSubject>().also { trie ->
            names.forEach { trie.add(assertNotNull(PhpStubs.function(it))) }
        }

    @Test
    fun `trie and single name matching accept the same complete records`() {
        val trie = trie()
        for (query in listOf(pattern("str", null), pattern(null, "str", null), pattern("str", null, "en"))) {
            val expected = names.filter(query::matches).toSet()
            assertEquals(
                expected,
                trie
                    .matches(query)
                    .asSequence()
                    .map { it.subject.name }
                    .toSet(),
            )
        }
    }

    @Test
    fun `negative and complete queries charge every visited node and output`() {
        val trie = trie()
        assertEquals(names.sumOf { it.length }, trie.insertedCharacters)
        val negative = trie.matches(pattern(null, "!", null))
        assertFalse(negative.hasNext())
        assertEquals(trie.nodeCount - 1, negative.visitedNodes)
        assertEquals(0, negative.emittedRecords)
        val all = trie.matches(pattern(null))
        assertEquals(names.toSet(), all.asSequence().map { it.subject.name }.toSet())
        assertEquals(trie.nodeCount - 1, all.visitedNodes)
        assertEquals(names.size, all.emittedRecords)
        assertTrue(all.maxFrames <= names.maxOf { it.length } + 1)
    }

    @Test
    fun `existence stops at its first match without changing later full queries`() {
        val trie = trie()
        val query = pattern("str", null)
        val existence = trie.matches(query)
        assertTrue(existence.hasNext())
        existence.next()
        assertEquals(1, existence.emittedRecords)
        val full = trie.matches(query)
        assertEquals(setOf("strlen", "strpos"), full.asSequence().map { it.subject.name }.toSet())
        assertTrue(existence.visitedNodes < full.visitedNodes)
    }

    @Test
    fun `effective merge indexes signatures before alias keys`() {
        val document =
            """
            - subject: {function: signed}
              signature: {params: [], returnType: string}
            - subject: {function: facts_only}
              returns: str
            - subject: {class: original}
              signature: {classifier: class, name: Original, aliases: [other]}
            """.trimIndent()
        val merge = SetMerge.of(listOf(TestSets.mount(0, Verification.MANUAL, document)))
        assertEquals(
            listOf("signed"),
            merge.functionNames
                .matches(pattern(null))
                .asSequence()
                .map { it.subject.name }
                .toList(),
        )
        assertEquals(
            listOf("original"),
            merge.classNames
                .matches(pattern(null))
                .asSequence()
                .map { it.subject.name }
                .toList(),
        )
        assertSame(merge.classes.values.first(), merge.classNames.matches(pattern(null)).next())
        assertTrue(merge.functions.containsKey(FunctionSubject("facts_only")))
    }

    @Test
    fun `independent effective merges do not share query results`() {
        val first =
            TestSets.mount(
                0,
                Verification.GENERATED,
                "- subject: {function: first}\n  signature: {params: [], returnType: string}\n",
            )
        val second =
            TestSets.mount(
                1,
                Verification.MANUAL,
                "- subject: {function: second}\n  signature: {params: [], returnType: int}\n",
            )
        val base = SetMerge.of(listOf(first))
        val extended = SetMerge.of(listOf(first, second))
        assertEquals(
            listOf("first"),
            base.functionNames
                .matches(pattern(null))
                .asSequence()
                .map { it.subject.name }
                .toList(),
        )
        assertEquals(
            listOf("first", "second"),
            extended.functionNames
                .matches(pattern(null))
                .asSequence()
                .map { it.subject.name }
                .toList(),
        )
    }

    @Test
    fun `query terminals use the effective signature and canonical namespace identity`() {
        val generated =
            TestSets.mount(
                0,
                Verification.GENERATED,
                "- subject: {class: 'vendor\\original'}\n" +
                    "  signature: {classifier: class, name: 'Vendor\\Original', aliases: ['oldalias']}\n",
            )
        val replacement =
            TestSets.mount(
                1,
                Verification.MANUAL,
                "- subject: {class: 'vendor\\original'}\n" +
                    "  signature: {classifier: interface, name: 'Vendor\\Original', aliases: ['newalias']}\n",
            )
        val first = SetMerge.of(listOf(generated))
        val effective = SetMerge.of(listOf(generated, replacement))
        val query = pattern("\\vendor\\", null)
        val result = effective.classNames.matches(query).next()
        assertSame(effective.classes.values.first(), result)
        assertEquals(listOf("newalias"), result.classSignature?.aliases)
        assertEquals(
            listOf("oldalias"),
            first.classNames
                .matches(query)
                .next()
                .classSignature
                ?.aliases,
        )
        assertFalse(effective.classNames.matches(pattern("new", null)).hasNext())
    }

    @Test
    fun `bundled matches include an unloaded function without creating a second record`() {
        val matched = PhpStubs.matchingFunctions(pattern("str", null)).toList()
        val strlen = matched.single { it.subject.name == "strlen" }
        assertSame(PhpStubs.function("strlen"), strlen)
        assertEquals(matched.size, matched.map { it.subject }.toSet().size)
        assertTrue(PhpStubs.matchingClasses(pattern("except", null)).any { it.subject.name == "exception" })
    }
}
