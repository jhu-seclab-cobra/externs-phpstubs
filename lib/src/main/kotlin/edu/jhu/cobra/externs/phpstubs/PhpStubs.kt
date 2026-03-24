package edu.jhu.cobra.externs.phpstubs

import java.io.DataInputStream
import java.io.InputStream

/**
 * Central registry for PHP built-in function, class, method, and constant stubs.
 *
 * Implements a **two-tier loading** strategy for optimal performance on high-frequency lookups:
 * - **Tier 1**: Immutable [Set]s of normalized keys, loaded eagerly on first access (~1 MB for 22K entries).
 *   Existence checks ([containsFunc], etc.) hit only this tier — O(1), zero allocation, zero synchronization.
 * - **Tier 2**: Raw serialized bytes stored in immutable [Map]s. Full [StubRecord] objects are deserialized
 *   lazily on first value access and cached in a lock-free [ConcurrentHashMap].
 *
 * **Thread safety**: All base data structures are immutable after the one-time [lazy] initialization.
 * The lazy delegate uses [LazyThreadSafetyMode.SYNCHRONIZED] so concurrent first-access is safe.
 * Subsequent reads are lock-free. The per-entry deserialization cache uses [ConcurrentHashMap.computeIfAbsent],
 * which is lock-free for existing keys.
 *
 * **No MapDB dependency**: reads a custom binary format (`.bin`) produced by the converter tool.
 */
object PhpStubs {

    private const val MAGIC = 0x43534253 // "CSBS"
    private const val VERSION: Byte = 1
    private const val DEFAULT_RESOURCE = "/stubs/builtin.bin"

    private val KEYWORD_FUNC_NAMES = setOf(
        "echo", "empty", "eval", "exit", "die", "isset",
        "print", "unset", "clone", "instanceof", "shell_exec",
        "include", "include_once", "require", "require_once",
    )

    private val SCALAR_TYPE_NAMES = setOf("int", "float", "string", "bool", "array")

    /**
     * Lazily loaded stub data. Thread-safe initialization via synchronized lazy delegate.
     * After init, the returned [StubData] is fully immutable.
     */
    private val data: StubData by lazy { loadDefault() }

    private fun loadDefault(): StubData {
        val stream = PhpStubs::class.java.getResourceAsStream(DEFAULT_RESOURCE)
            ?: return StubData.EMPTY
        return loadFromStream(stream)
    }

    /**
     * Loads stub data from a binary input stream.
     *
     * @throws StubIndexInvalidException If the binary format is invalid.
     */
    fun loadFromStream(stream: InputStream): StubData {
        DataInputStream(stream.buffered()).use { input ->
            val magic = input.readInt()
            if (magic != MAGIC) throw StubIndexInvalidException("Bad magic: 0x${magic.toString(16)}, expected 0x${MAGIC.toString(16)}")
            val version = input.readByte()
            if (version != VERSION) throw StubIndexInvalidException("Unsupported version: $version")

            val functions = readSection(input)
            val classes = readSection(input)
            val methods = readSection(input)
            val constants = readSection(input)
            return StubData(functions, classes, methods, constants)
        }
    }

    private fun readSection(input: DataInputStream): StubSection {
        val count = input.readInt()
        val keys = LinkedHashSet<String>(count * 2)
        val rawData = HashMap<String, ByteArray>(count * 2)
        repeat(count) {
            val key = input.readUTF()
            val valueSize = input.readInt()
            val valueBytes = ByteArray(valueSize).also { input.readFully(it) }
            keys.add(key)
            rawData[key] = valueBytes
        }
        return StubSection(keys.toSet(), rawData.toMap())
    }

    private fun String.normalize(): String = lowercase().removePrefix("/")

    // -- Existence checks (Tier 1 — hot path, zero allocation) --

    /**
     * Checks if the given name is a known built-in function or keyword.
     */
    fun containsFunc(name: String): Boolean {
        val key = name.normalize()
        return data.functions.contains(key) || key in KEYWORD_FUNC_NAMES
    }

    /**
     * Checks if the given name is a known built-in class or scalar type.
     */
    fun containsClass(name: String): Boolean {
        val key = name.normalize()
        return data.classes.contains(key) || key in SCALAR_TYPE_NAMES || key == "exit" || key == "resource"
    }

    /**
     * Checks if the given method exists in the stub index.
     *
     * @param methodName The method name.
     * @param className The owning class, or null to search by suffix across all classes.
     */
    fun containsMethod(methodName: String, className: String? = null): Boolean {
        if (className != null) {
            return data.methods.contains("${className.normalize()}::${methodName.normalize()}")
        }
        val suffix = "::${methodName.normalize()}"
        return data.methods.keys.any { it.endsWith(suffix) }
    }

    /**
     * Checks if the given constant exists in the stub index.
     */
    fun containsConst(name: String): Boolean = data.constants.contains(name.normalize())

    // -- Full record retrieval (Tier 2 — cold path, lazy deserialization) --

    /**
     * Searches for a built-in function by name.
     *
     * @return [StubRecord] if found in the index or keyword set; null otherwise.
     */
    fun searchFunc(name: String): StubRecord? {
        val key = name.normalize()
        return data.functions.get(key)
            ?: if (key in KEYWORD_FUNC_NAMES) StubRecord(name = key, extension = "keyword") else null
    }

    /**
     * Searches for a built-in class by name.
     *
     * @return [StubRecord] if found; synthetic records for scalar types, "exit", "resource"; null otherwise.
     */
    fun searchClass(name: String): StubRecord? {
        val key = name.normalize()
        return data.classes.get(key) ?: when (key) {
            in SCALAR_TYPE_NAMES -> StubRecord(name = key, extension = "Scalar")
            "exit" -> StubRecord(name = key, extension = "Core")
            "resource" -> StubRecord(name = key, extension = "legacy")
            else -> null
        }
    }

    /**
     * Searches for a built-in method.
     *
     * @param methodName The method name.
     * @param className The owning class name, or null to search by suffix.
     * @return A pair of (fully-qualified name, [StubRecord]) if found; null otherwise.
     */
    fun searchMethod(methodName: String, className: String? = null): Pair<String, StubRecord>? {
        if (className != null) {
            val fullName = "${className.normalize()}::${methodName.normalize()}"
            return data.methods.get(fullName)?.let { fullName to it }
        }
        val suffix = "::${methodName.normalize()}"
        val matchKey = data.methods.keys.firstOrNull { it.endsWith(suffix) } ?: return null
        return data.methods.get(matchKey)?.let { matchKey to it }
    }

    /**
     * Searches for a built-in global constant.
     */
    fun searchGlobalConst(name: String): StubRecord? = data.constants.get(name.normalize())

    /**
     * Searches for a built-in class constant.
     *
     * @param constName The constant name.
     * @param className The owning class, or null to search by suffix.
     */
    fun searchClassConst(constName: String, className: String? = null): StubRecord? {
        if (className != null) {
            return data.constants.get("${className.normalize()}::${constName.normalize()}")
        }
        val suffix = "::${constName.normalize()}"
        val matchKey = data.constants.keys.firstOrNull { it.endsWith(suffix) } ?: return null
        return data.constants.get(matchKey)
    }

    // -- Accessors --

    fun getAllFuncNames(): Set<String> = data.functions.keys
    fun getAllClassNames(): Set<String> = data.classes.keys
    fun getAllMethodNames(): Set<String> = data.methods.keys
    fun getAllConstNames(): Set<String> = data.constants.keys
    fun getKeywordFuncNames(): Set<String> = KEYWORD_FUNC_NAMES
    fun getScalarTypeNames(): Set<String> = SCALAR_TYPE_NAMES

    /**
     * Returns the raw serialized bytes for a function entry, for consumers that need
     * to deserialize the original IValue themselves (e.g., via DftByteArraySerializerImpl).
     */
    fun getFuncRawData(name: String): ByteArray? = data.functions.rawData[name.normalize()]

    /**
     * Returns the raw serialized bytes for a class entry.
     */
    fun getClassRawData(name: String): ByteArray? = data.classes.rawData[name.normalize()]

    /**
     * Returns the raw serialized bytes for a method entry.
     */
    fun getMethodRawData(name: String, className: String? = null): ByteArray? {
        if (className != null) {
            return data.methods.rawData["${className.normalize()}::${name.normalize()}"]
        }
        val suffix = "::${name.normalize()}"
        val matchKey = data.methods.rawData.keys.firstOrNull { it.endsWith(suffix) }
        return matchKey?.let { data.methods.rawData[it] }
    }

    /**
     * Returns the raw serialized bytes for a constant entry.
     */
    fun getConstRawData(name: String): ByteArray? = data.constants.rawData[name.normalize()]
}

/**
 * Immutable container for all four stub sections. Thread-safe by construction.
 */
class StubData(
    val functions: StubSection,
    val classes: StubSection,
    val methods: StubSection,
    val constants: StubSection,
) {
    companion object {
        val EMPTY = StubData(StubSection.EMPTY, StubSection.EMPTY, StubSection.EMPTY, StubSection.EMPTY)
    }
}
