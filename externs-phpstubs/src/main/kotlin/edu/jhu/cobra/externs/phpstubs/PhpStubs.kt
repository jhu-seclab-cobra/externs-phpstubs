package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.value.ListVal
import edu.jhu.cobra.commons.value.StrVal
import java.io.DataInputStream
import java.io.InputStream

/**
 * Central registry for PHP built-in function, class, method, and constant stubs.
 *
 * Implements a **two-tier loading** strategy for optimal performance on high-frequency lookups:
 * - **Tier 1**: Immutable [Set]s of normalized keys, loaded eagerly on first access (~1 MB for 22K entries).
 *   Existence checks ([containsFunc], etc.) hit only this tier — O(1), zero allocation, zero synchronization.
 * - **Tier 2**: Raw serialized bytes stored in immutable [Map]s. Full [StubRecord] objects (including
 *   deserialized [IValue]) are constructed lazily on first value access and cached in a lock-free
 *   [java.util.concurrent.ConcurrentHashMap].
 *
 * **Thread safety**: All base data structures are immutable after the one-time [lazy] initialization.
 * The lazy delegate uses [LazyThreadSafetyMode.SYNCHRONIZED] so concurrent first-access is safe.
 * Subsequent reads are lock-free. The per-entry deserialization cache uses
 * [java.util.concurrent.ConcurrentHashMap.computeIfAbsent], which is lock-free for existing keys.
 *
 * **Dependencies**: Requires `commons-value` for [IValue] deserialization. No MapDB dependency.
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

    private val KEYWORD_RECORDS: Map<String, StubRecord> = KEYWORD_FUNC_NAMES.associateWith { name ->
        StubRecord(name = name, extension = "keyword", value = ListVal(StrVal("keyword")))
    }

    private val SYNTHETIC_CLASS_RECORDS: Map<String, StubRecord> = buildMap {
        for (name in SCALAR_TYPE_NAMES) {
            put(name, StubRecord(name = name, extension = "Scalar", value = ListVal(StrVal("Scalar"))))
        }
        put("exit", StubRecord(name = "exit", extension = "Core", value = ListVal(StrVal("Core"))))
        put("resource", StubRecord(name = "resource", extension = "legacy", value = ListVal(StrVal("legacy"))))
    }

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
        return StubSection(
            java.util.Collections.unmodifiableSet(keys),
            java.util.Collections.unmodifiableMap(rawData),
        )
    }

    private fun String.normalize(): String {
        val stripped = if (startsWith('/')) substring(1) else this
        // Fast path: if already all-lowercase ASCII, return without allocation
        var allLower = true
        for (c in stripped) {
            if (c in 'A'..'Z') { allLower = false; break }
        }
        return if (allLower) stripped else stripped.lowercase()
    }

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
        return data.methods.containsBySuffix(methodName.normalize())
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
        return data.functions.get(key) ?: KEYWORD_RECORDS[key]
    }

    /**
     * Searches for a built-in class by name.
     *
     * @return [StubRecord] if found; synthetic records for scalar types, "exit", "resource"; null otherwise.
     */
    fun searchClass(name: String): StubRecord? {
        val key = name.normalize()
        return data.classes.get(key) ?: SYNTHETIC_CLASS_RECORDS[key]
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
        val matchKey = data.methods.findKeyBySuffix(methodName.normalize()) ?: return null
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
        val matchKey = data.constants.findKeyBySuffix(constName.normalize()) ?: return null
        return data.constants.get(matchKey)
    }

    // -- Accessors --

    fun getAllFuncNames(): Set<String> = data.functions.keys
    fun getAllClassNames(): Set<String> = data.classes.keys
    fun getAllMethodNames(): Set<String> = data.methods.keys
    fun getAllConstNames(): Set<String> = data.constants.keys
    fun getKeywordFuncNames(): Set<String> = KEYWORD_FUNC_NAMES
    fun getScalarTypeNames(): Set<String> = SCALAR_TYPE_NAMES
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
