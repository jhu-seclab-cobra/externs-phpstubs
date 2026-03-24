package edu.jhu.cobra.externs.phpstubs

import java.util.concurrent.ConcurrentHashMap

/**
 * An immutable, thread-safe section of stub data implementing two-tier loading.
 *
 * - **Tier 1 (hot path)**: [keys] is an immutable [Set] for O(1) existence checks with zero synchronization.
 * - **Tier 2 (cold path)**: [rawData] holds compact serialized bytes; deserialization into [StubRecord]
 *   happens lazily on first access per key, cached in a lock-free [ConcurrentHashMap].
 *
 * All fields are assigned once at construction and never mutated, so concurrent reads are safe
 * without any locking on the hot path.
 *
 * @property keys Immutable set of all normalized keys in this section.
 * @property rawData Immutable map of key → serialized value bytes (from [DftByteArraySerializerImpl]).
 */
class StubSection internal constructor(
    val keys: Set<String>,
    val rawData: Map<String, ByteArray>,
) {
    private val cache = ConcurrentHashMap<String, StubRecord>()

    /**
     * O(1) existence check. No allocation, no synchronization.
     */
    fun contains(key: String): Boolean = key in keys

    /**
     * Returns a [StubRecord] for the given key, deserializing lazily on first access.
     * Subsequent calls for the same key return the cached instance with no synchronization overhead
     * (ConcurrentHashMap.computeIfAbsent is lock-free on existing keys).
     *
     * @return The [StubRecord], or null if the key is not in this section.
     */
    fun get(key: String): StubRecord? {
        if (key !in keys) return null
        return cache.computeIfAbsent(key) { k ->
            StubRecord(name = k, extension = extractExtension(rawData[k]!!))
        }
    }

    /**
     * Returns all entries, deserializing any that haven't been accessed yet.
     */
    fun getAll(): Map<String, StubRecord> {
        for (key in keys) get(key)
        return cache.toMap()
    }

    companion object {
        val EMPTY = StubSection(emptySet(), emptyMap())

        /**
         * Extracts the extension name from the first element of a serialized ListVal.
         * ListVal format: [0x0C (LIST type)] [4-byte element size] [0x01 (STR type)] [UTF-8 bytes...]
         *
         * For non-ListVal formats (e.g., MapVal for constants), falls back to "unknown".
         */
        internal fun extractExtension(bytes: ByteArray): String {
            if (bytes.isEmpty()) return "unknown"
            return when (bytes[0]) {
                0x0C.toByte() -> { // LIST type tag
                    if (bytes.size < 6) return "unknown"
                    // Skip LIST tag (1) + element size (4) + STR tag (1) = offset 6
                    val strStart = 6
                    val elementSize = ((bytes[1].toInt() and 0xFF) shl 24) or
                        ((bytes[2].toInt() and 0xFF) shl 16) or
                        ((bytes[3].toInt() and 0xFF) shl 8) or
                        (bytes[4].toInt() and 0xFF)
                    val strLen = elementSize - 1 // minus STR type tag
                    if (strStart + strLen > bytes.size) return "unknown"
                    String(bytes, strStart, strLen, Charsets.UTF_8)
                }
                0x01.toByte() -> { // STR type tag (direct string)
                    String(bytes, 1, bytes.size - 1, Charsets.UTF_8)
                }
                else -> "unknown"
            }
        }
    }
}
