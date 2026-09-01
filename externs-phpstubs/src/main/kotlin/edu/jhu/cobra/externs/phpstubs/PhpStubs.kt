package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject

/**
 * PHP built-in declaration registry: existence checks and entry lookups by PHP name.
 *
 * Qualified lookups build their subject through the commons-phpmodels creators, so a name that is not a PHP
 * identifier spelling raises [IllegalArgumentException]. Unqualified member lookups and case-insensitive
 * constant lookups read prebuilt indexes and are over-approximations for analyses that cannot trust spelling.
 */
public object PhpStubs {
    // Extension names fixed by the language document layout: models/language/<extension>.yaml.
    private const val KEYWORD_EXTENSION = "keyword"
    private const val SCALAR_EXTENSION = "scalar"
    private const val MEMBER_SEPARATOR = "::"

    private val registry: StubRegistry by lazy { StubLoader.loadAll() }

    // Unqualified member name -> first subject in load order.
    private val methodSuffixIndex: Map<String, MethodSubject> by lazy {
        firstByKey(registry.methods.keys) { it.name }
    }
    private val classConstSuffixIndex: Map<String, ClassConstantSubject> by lazy {
        firstByKey(registry.classConstants.keys) { it.name }
    }
    private val classConstSuffixFoldedIndex: Map<String, ClassConstantSubject> by lazy {
        firstByKey(registry.classConstants.keys) { it.name.lowercase() }
    }

    // Folded spelling -> first subject in load order, for case-insensitive constant lookup.
    private val constFoldedIndex: Map<String, ConstantSubject> by lazy {
        firstByKey(registry.constants.keys) { it.name.lowercase() }
    }
    private val classConstFoldedIndex: Map<String, ClassConstantSubject> by lazy {
        firstByKey(registry.classConstants.keys) { it.owner + MEMBER_SEPARATOR + it.name.lowercase() }
    }

    private val functionNames: Set<String> by lazy { registry.functions.keys.mapTo(LinkedHashSet()) { it.name } }
    private val classNames: Set<String> by lazy { registry.classes.keys.mapTo(LinkedHashSet()) { it.name } }
    private val methodNames: Set<String> by lazy {
        registry.methods.keys.mapTo(LinkedHashSet()) { it.owner + MEMBER_SEPARATOR + it.name }
    }
    private val constantNames: Set<String> by lazy { registry.constants.keys.mapTo(LinkedHashSet()) { it.name } }
    private val keywordFunctionNames: Set<String> by lazy { functionNamesOfExtension(KEYWORD_EXTENSION) }
    private val scalarClassNames: Set<String> by lazy { classNamesOfExtension(SCALAR_EXTENSION) }

    private fun <S> firstByKey(
        subjects: Set<S>,
        key: (S) -> String,
    ): Map<String, S> {
        val index = LinkedHashMap<String, S>()
        for (subject in subjects) index.putIfAbsent(key(subject), subject)
        return index
    }

    private fun functionNamesOfExtension(extension: String): Set<String> =
        registry.functions.values
            .filter { it.extension == extension }
            .mapTo(LinkedHashSet()) { it.subject.name }

    private fun classNamesOfExtension(extension: String): Set<String> =
        registry.classes.values
            .filter { it.extension == extension }
            .mapTo(LinkedHashSet()) { it.subject.name }

    // -- Existence checks --

    /** Returns true if [name] is a known built-in or language-construct function. */
    public fun containsFunc(name: String): Boolean = FunctionSubject.parse(name) in registry.functions

    /** Returns true if [name] is a known built-in, scalar-type, or language-construct class. */
    public fun containsClass(name: String): Boolean = ClassSubject.parse(name) in registry.classes

    /** Returns true if the method exists: qualified when [className] is given, by unqualified name otherwise. */
    public fun containsMethod(
        methodName: String,
        className: String? = null,
    ): Boolean = searchMethod(methodName, className) != null

    /** Returns true if [name] is a known global constant, or a known class constant when spelled `Class::NAME`. */
    public fun containsConst(
        name: String,
        caseSensitive: Boolean = true,
    ): Boolean =
        if (MEMBER_SEPARATOR in name) {
            val spelled = ClassConstantSubject.parse(name)
            searchClassConst(spelled.name, spelled.owner, caseSensitive) != null
        } else {
            searchGlobalConst(name, caseSensitive) != null
        }

    // -- Entry retrieval --

    /** Returns the function entry for [name], or null if unknown. */
    public fun searchFunc(name: String): StubEntry<FunctionSubject>? = registry.functions[FunctionSubject.parse(name)]

    /** Returns the class entry for [name], or null if unknown. */
    public fun searchClass(name: String): StubEntry<ClassSubject>? = registry.classes[ClassSubject.parse(name)]

    /** Returns the method entry: qualified when [className] is given, first unqualified match otherwise. */
    public fun searchMethod(
        methodName: String,
        className: String? = null,
    ): StubEntry<MethodSubject>? {
        val subject =
            if (className == null) {
                methodSuffixIndex[methodName.lowercase()]
            } else {
                MethodSubject(ClassSubject.parse(className).name, methodName)
            }
        return subject?.let { registry.methods[it] }
    }

    /** Returns the global constant entry for [name], exact by default or folded when [caseSensitive] is false. */
    public fun searchGlobalConst(
        name: String,
        caseSensitive: Boolean = true,
    ): StubEntry<ConstantSubject>? {
        val spelled = ConstantSubject.parse(name)
        val subject = if (caseSensitive) spelled else constFoldedIndex[spelled.name.lowercase()]
        return subject?.let { registry.constants[it] }
    }

    /** Returns the class constant entry: qualified when [className] is given, first unqualified match otherwise. */
    public fun searchClassConst(
        constName: String,
        className: String? = null,
        caseSensitive: Boolean = true,
    ): StubEntry<ClassConstantSubject>? {
        val subject =
            if (className == null) {
                unqualifiedClassConst(constName, caseSensitive)
            } else {
                qualifiedClassConst(constName, className, caseSensitive)
            }
        return subject?.let { registry.classConstants[it] }
    }

    private fun unqualifiedClassConst(
        constName: String,
        caseSensitive: Boolean,
    ): ClassConstantSubject? = if (caseSensitive) classConstSuffixIndex[constName] else classConstSuffixFoldedIndex[constName.lowercase()]

    private fun qualifiedClassConst(
        constName: String,
        className: String,
        caseSensitive: Boolean,
    ): ClassConstantSubject? {
        val spelled = ClassConstantSubject(ClassSubject.parse(className).name, constName)
        if (caseSensitive) return spelled
        return classConstFoldedIndex[spelled.owner + MEMBER_SEPARATOR + spelled.name.lowercase()]
    }

    // -- Bulk access --

    /** All registered function names, folded. Language constructs included. */
    public fun getAllFuncNames(): Set<String> = functionNames

    /** All registered class names, folded. Scalar types and language constructs included. */
    public fun getAllClassNames(): Set<String> = classNames

    /** All registered method spellings as `owner::name`, folded. */
    public fun getAllMethodNames(): Set<String> = methodNames

    /** All registered global constant names, case preserved. Class constants are not included. */
    public fun getAllConstNames(): Set<String> = constantNames

    /** PHP keyword construct names (echo, isset, ...): the functions of the `keyword` extension. */
    public fun getKeywordFuncNames(): Set<String> = keywordFunctionNames

    /** PHP scalar type names (int, string, ...): the classes of the `scalar` extension. */
    public fun getScalarTypeNames(): Set<String> = scalarClassNames
}
