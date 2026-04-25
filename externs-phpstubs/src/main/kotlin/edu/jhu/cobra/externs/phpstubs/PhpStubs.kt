package edu.jhu.cobra.externs.phpstubs

/**
 * Central registry for PHP built-in function, class, method, and constant stubs.
 *
 * Loads a [StubRegistry] from YAML stub files on first access. Provides normalized
 * lookup and existence-check methods for all entity categories. Keyword functions
 * and scalar type names are handled via in-memory synthetic records.
 */
object PhpStubs {

    private val KEYWORD_FUNC_NAMES = setOf(
        "echo", "empty", "eval", "exit", "die", "isset",
        "print", "unset", "clone", "instanceof", "shell_exec",
        "include", "include_once", "require", "require_once",
    )

    private val SCALAR_TYPE_NAMES = setOf("int", "float", "string", "bool", "array")

    private val KEYWORD_RECORDS: Map<String, StubRecord.Function> =
        KEYWORD_FUNC_NAMES.associateWith { name ->
            StubRecord.Function(name = name, extension = "keyword")
        }

    private val SYNTHETIC_CLASS_RECORDS: Map<String, StubRecord.PhpClass> = buildMap {
        for (name in SCALAR_TYPE_NAMES) {
            put(name, StubRecord.PhpClass(name = name, extension = "Scalar"))
        }
        put("exit", StubRecord.PhpClass(name = "exit", extension = "Core"))
        put("resource", StubRecord.PhpClass(name = "resource", extension = "legacy"))
    }

    private val registry: StubRegistry by lazy { loadRegistry() }

    /** Suffix → full key index for methods (built lazily). */
    private val methodSuffixIndex: Map<String, String> by lazy {
        buildSuffixIndex(registry.methods.keys)
    }

    /** Suffix → full key index for class constants (built lazily). */
    private val classConstSuffixIndex: Map<String, String> by lazy {
        buildSuffixIndex(registry.classConstants.keys)
    }

    private fun loadRegistry(): StubRegistry =
        try {
            StubLoader.loadAll()
        } catch (_: StubIndexNotFoundException) {
            StubRegistry(
                functions = emptyMap(),
                classes = emptyMap(),
                methods = emptyMap(),
                constants = emptyMap(),
                classConstants = emptyMap(),
                properties = emptyMap(),
            )
        }

    private fun buildSuffixIndex(keys: Set<String>): Map<String, String> {
        val index = mutableMapOf<String, String>()
        for (key in keys) {
            val sep = key.indexOf("::")
            if (sep < 0) continue
            val suffix = key.substring(sep + 2)
            index.putIfAbsent(suffix, key)
        }
        return index
    }

    // -- Existence checks --

    fun containsFunc(name: String): Boolean {
        val key = name.normalize()
        return key in registry.functions || key in KEYWORD_FUNC_NAMES
    }

    fun containsClass(name: String): Boolean {
        val key = name.normalize()
        return key in registry.classes || key in SYNTHETIC_CLASS_RECORDS
    }

    fun containsMethod(methodName: String, className: String? = null): Boolean {
        if (className != null) {
            return "${className.normalize()}::${methodName.normalize()}" in registry.methods
        }
        return methodName.normalize() in methodSuffixIndex
    }

    fun containsConst(name: String): Boolean {
        val key = name.normalize()
        return key in registry.constants || key in registry.classConstants
    }

    // -- Record retrieval --

    fun searchFunc(name: String): StubRecord.Function? {
        val key = name.normalize()
        return KEYWORD_RECORDS[key] ?: registry.functions[key]
    }

    fun searchClass(name: String): StubRecord.PhpClass? {
        val key = name.normalize()
        return registry.classes[key] ?: SYNTHETIC_CLASS_RECORDS[key]
    }

    fun searchMethod(methodName: String, className: String? = null): Pair<String, StubRecord.Method>? {
        if (className != null) {
            val fullName = "${className.normalize()}::${methodName.normalize()}"
            return registry.methods[fullName]?.let { fullName to it }
        }
        val fullKey = methodSuffixIndex[methodName.normalize()] ?: return null
        return registry.methods[fullKey]?.let { fullKey to it }
    }

    fun searchGlobalConst(name: String): StubRecord.Constant? =
        registry.constants[name.normalize()]

    fun searchClassConst(constName: String, className: String? = null): StubRecord.ClassConstant? {
        if (className != null) {
            return registry.classConstants["${className.normalize()}::${constName.normalize()}"]
        }
        val fullKey = classConstSuffixIndex[constName.normalize()] ?: return null
        return registry.classConstants[fullKey]
    }

    // -- Bulk access --

    fun getAllFuncNames(): Set<String> = registry.functions.keys
    fun getAllClassNames(): Set<String> = registry.classes.keys
    fun getAllMethodNames(): Set<String> = registry.methods.keys
    fun getAllConstNames(): Set<String> = registry.constants.keys
    fun getKeywordFuncNames(): Set<String> = KEYWORD_FUNC_NAMES
    fun getScalarTypeNames(): Set<String> = SCALAR_TYPE_NAMES

    /** Strips leading slash (forward or back) and lowercases. */
    internal fun String.normalize(): String {
        val stripped = if (startsWith('/') || startsWith('\\')) substring(1) else this
        var allLower = true
        for (c in stripped) {
            if (c in 'A'..'Z') { allLower = false; break }
        }
        return if (allLower) stripped else stripped.lowercase()
    }
}
