package edu.jhu.cobra.externs.phpstubs

/** PHP built-in entity registry. Normalized lookup and existence checks for functions, classes, methods, and constants. */
public object PhpStubs {
    private val KEYWORD_FUNC_NAMES =
        setOf(
            "echo",
            "empty",
            "eval",
            "exit",
            "die",
            "isset",
            "print",
            "unset",
            "clone",
            "instanceof",
            "shell_exec",
            "include",
            "include_once",
            "require",
            "require_once",
        )

    private val SCALAR_TYPE_NAMES = setOf("int", "float", "string", "bool", "array")

    private val KEYWORD_RECORDS: Map<String, StubRecord.Function> =
        KEYWORD_FUNC_NAMES.associateWith { name ->
            StubRecord.Function(name = name, extension = "keyword")
        }

    private val SYNTHETIC_CLASS_RECORDS: Map<String, StubRecord.PhpClass> =
        buildMap {
            for (name in SCALAR_TYPE_NAMES) {
                put(name, StubRecord.PhpClass(name = name, extension = "Scalar"))
            }
            put("exit", StubRecord.PhpClass(name = "exit", extension = "Core"))
            put("resource", StubRecord.PhpClass(name = "resource", extension = "legacy"))
        }

    private val registry: StubRegistry by lazy { StubLoader.loadAll() }

    // Suffix → full key index for methods.
    private val methodSuffixIndex: Map<String, String> by lazy {
        buildSuffixIndex(registry.methods.keys)
    }

    // Suffix → full key index for class constants (case-preserved suffix).
    private val classConstSuffixIndex: Map<String, String> by lazy {
        buildSuffixIndex(registry.classConstants.keys)
    }

    // Normalized key → original key for case-insensitive constant lookup.
    private val constCiIndex: Map<String, String> by lazy {
        registry.constants.keys.associateBy { it.lowercase() }
    }

    // Normalized key → original key for case-insensitive class constant lookup.
    private val classConstCiIndex: Map<String, String> by lazy {
        registry.classConstants.keys.associateBy { it.lowercase() }
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

    /** Returns true if [name] is a known built-in or keyword function. */
    public fun containsFunc(name: String): Boolean {
        val key = name.normalize()
        return key in registry.functions || key in KEYWORD_FUNC_NAMES
    }

    /** Returns true if [name] is a known built-in or scalar class. */
    public fun containsClass(name: String): Boolean {
        val key = name.normalize()
        return key in registry.classes || key in SYNTHETIC_CLASS_RECORDS
    }

    /** Returns true if the method exists. Checks "class::method" when [className] provided, otherwise matches by suffix. */
    public fun containsMethod(
        methodName: String,
        className: String? = null,
    ): Boolean {
        if (className != null) {
            return "${className.normalize()}::${methodName.normalize()}" in registry.methods
        }
        return methodName.normalize() in methodSuffixIndex
    }

    /** Returns true if [name] is a known global or class constant. */
    public fun containsConst(
        name: String,
        caseSensitive: Boolean = true,
    ): Boolean {
        val stripped = name.stripLeadingSlash()
        if (caseSensitive) return stripped in registry.constants || stripped in registry.classConstants
        val lower = stripped.lowercase()
        return lower in constCiIndex || lower in classConstCiIndex
    }

    // -- Record retrieval --

    /** Returns the function stub record for [name], or null if unknown. */
    public fun searchFunc(name: String): StubRecord.Function? {
        val key = name.normalize()
        return KEYWORD_RECORDS[key] ?: registry.functions[key]
    }

    /** Returns the class stub record for [name], or null if unknown. */
    public fun searchClass(name: String): StubRecord.PhpClass? {
        val key = name.normalize()
        return registry.classes[key] ?: SYNTHETIC_CLASS_RECORDS[key]
    }

    /** Returns (fullKey, method) for the given method, or null if unknown. */
    public fun searchMethod(
        methodName: String,
        className: String? = null,
    ): Pair<String, StubRecord.Method>? {
        if (className != null) {
            val fullName = "${className.normalize()}::${methodName.normalize()}"
            return registry.methods[fullName]?.let { fullName to it }
        }
        val fullKey = methodSuffixIndex[methodName.normalize()] ?: return null
        return registry.methods[fullKey]?.let { fullKey to it }
    }

    /** Returns the global constant stub record for [name], or null if unknown. */
    public fun searchGlobalConst(
        name: String,
        caseSensitive: Boolean = true,
    ): StubRecord.Constant? {
        val stripped = name.stripLeadingSlash()
        if (caseSensitive) return registry.constants[stripped]
        val key = constCiIndex[stripped.lowercase()] ?: return null
        return registry.constants[key]
    }

    /** Returns the class constant stub record, or null if unknown. */
    public fun searchClassConst(
        constName: String,
        className: String? = null,
        caseSensitive: Boolean = true,
    ): StubRecord.ClassConstant? {
        val strippedConst = constName.stripLeadingSlash()
        if (className != null) {
            val clsKey = className.normalize()
            val fullKey = if (caseSensitive) "$clsKey::$strippedConst" else "$clsKey::${strippedConst.lowercase()}"
            if (caseSensitive) return registry.classConstants[fullKey]
            val originalKey = classConstCiIndex[fullKey] ?: return null
            return registry.classConstants[originalKey]
        }
        val suffix = if (caseSensitive) strippedConst else strippedConst.lowercase()
        val fullKey = classConstSuffixIndex[suffix] ?: return null
        return registry.classConstants[fullKey]
    }

    // -- Bulk access --

    /** All registered built-in function names. */
    public fun getAllFuncNames(): Set<String> = registry.functions.keys

    /** All registered built-in class names. */
    public fun getAllClassNames(): Set<String> = registry.classes.keys

    /** All registered built-in method names. */
    public fun getAllMethodNames(): Set<String> = registry.methods.keys

    /** All registered global constant names. Class constants are not included. */
    public fun getAllConstNames(): Set<String> = registry.constants.keys

    /** PHP keyword function names (echo, isset, etc.). */
    public fun getKeywordFuncNames(): Set<String> = KEYWORD_FUNC_NAMES

    /** PHP scalar type names (int, string, etc.). */
    public fun getScalarTypeNames(): Set<String> = SCALAR_TYPE_NAMES

    internal fun String.stripLeadingSlash(): String = if (startsWith('/') || startsWith('\\')) substring(1) else this

    /** Strips leading slash and lowercases. For case-insensitive entities (functions, classes, methods). */
    internal fun String.normalize(): String = stripLeadingSlash().lowercase()
}
