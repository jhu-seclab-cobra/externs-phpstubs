package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * The name-trie condition a byte-matching consumer relies on.
 * - `every bundled trie name is ASCII` checks the function and class names of the bundled merge and of each Library
 *   Set, so the characters of each name are its bytes.
 */
internal class BuiltinNameAsciiTest {
    private val any = NamePattern(listOf(NamePattern.Part.Gap))

    private fun nonAscii(lookup: BuiltinLookup): List<String> =
        (lookup.matchingFunctions(any).map { it.subject.name } + lookup.matchingClasses(any).map { it.subject.name })
            .filter { name -> name.any { it.code >= 0x80 } }
            .toList()

    @Test
    fun `every bundled trie name is ASCII`() {
        assertEquals(emptyList(), nonAscii(PhpStubs))
        for (library in PhpStubs.libraries) {
            assertEquals(emptyList(), nonAscii(PhpStubs.withLibraries(library.`package`)), library.`package`)
        }
    }
}
