package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.value.IValue
import edu.jhu.cobra.commons.value.ListVal
import edu.jhu.cobra.commons.value.StrVal
import edu.jhu.cobra.commons.value.serializer.DftByteArraySerializerImpl
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
 * @property rawData Immutable map of key to serialized value bytes.
 */
class StubSection internal constructor(
    val keys: Set<String>,
    internal val rawData: Map<String, ByteArray>,
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
            val bytes = rawData[k]!!
            val value = DftByteArraySerializerImpl.deserialize(bytes)
            StubRecord(name = k, extension = extractExtension(value), value = value)
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
         * Extracts the extension name from a deserialized [IValue].
         * For [ListVal], the first element is the extension name string.
         * For [StrVal], the string itself is the extension name.
         */
        internal fun extractExtension(value: IValue): String = when (value) {
            is ListVal -> (value.core.firstOrNull() as? StrVal)?.core ?: "unknown"
            is StrVal -> value.core
            else -> "unknown"
        }
    }
}
