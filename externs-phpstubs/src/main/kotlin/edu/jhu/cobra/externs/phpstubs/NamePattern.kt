package edu.jhu.cobra.externs.phpstubs

/**
 * A complete canonical-name query made of literal text and independent abstract gaps.
 *
 * The consumer folds literal text according to its name policy. Each gap accepts any string, including empty,
 * regardless of whether another occurrence had the same source. A canonical name may have one leading root separator.
 * The pattern stores no graph identity, label or query result.
 */
public class NamePattern(
    parts: List<Part>,
) {
    /** One literal segment or one unresolved abstract occurrence. */
    public sealed interface Part {
        /** Known text remains literal, including characters that a regex would treat specially. */
        public data class Literal(
            val text: String,
        ) : Part

        /** One independent possibly empty string. */
        public data object Gap : Part
    }

    private val symbols: List<Char?> =
        parts.flatMap { part ->
            when (part) {
                is Part.Literal -> part.text.toList()
                Part.Gap -> listOf(null)
            }
        }

    internal val width: Int = symbols.size + 1

    /** Whether the entire canonical spelling is accepted; no prefix-only or display-marker matching. */
    public fun matches(canonicalName: String): Boolean {
        var state = initial()
        for (character in canonicalName) state = advance(state, character)
        return accepts(state)
    }

    internal fun initial(): BooleanArray {
        val bare = BooleanArray(width)
        bare[0] = true
        close(bare)
        val rooted = advance(bare, '\\')
        for (index in bare.indices) bare[index] = bare[index] || rooted[index]
        return bare
    }

    internal fun advance(
        state: BooleanArray,
        character: Char,
    ): BooleanArray {
        val next = BooleanArray(width)
        for (index in symbols.indices) {
            if (!state[index]) continue
            val symbol = symbols[index]
            if (symbol == null) {
                next[index] = true
            } else if (symbol == character) {
                next[index + 1] = true
            }
        }
        close(next)
        return next
    }

    internal fun accepts(state: BooleanArray): Boolean = state[symbols.size]

    private fun close(state: BooleanArray) {
        for (index in symbols.indices) {
            if (state[index] && symbols[index] == null) state[index + 1] = true
        }
    }
}
