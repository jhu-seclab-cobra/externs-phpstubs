package edu.jhu.cobra.externs.phpstubs

/**
 * Immutable record representing a PHP built-in entity parsed from unified YAML stubs.
 * Each subtype carries only the fields relevant to its entity kind.
 *
 * @property name Entity name (e.g., "strlen", "Exception", "PHP_INT_MAX").
 * @property extension PHP extension this entity belongs to (e.g., "standard", "core").
 */
sealed class StubRecord {
    abstract val name: String
    abstract val extension: String

    /** Top-level PHP function. */
    data class Function(
        override val name: String,
        override val extension: String,
        val params: List<StubParam> = emptyList(),
        val returnType: PhpType = PhpType.MIXED,
        val flowsToReturn: Set<Int> = emptySet(),
    ) : StubRecord()

    /** Class method. */
    data class Method(
        override val name: String,
        override val extension: String,
        val owningClass: String,
        val params: List<StubParam> = emptyList(),
        val returnType: PhpType = PhpType.MIXED,
        val flowsToReturn: Set<Int> = emptySet(),
        val visibility: Visibility = Visibility.PUBLIC,
        val isStatic: Boolean = false,
    ) : StubRecord()

    /** Class or interface definition. */
    data class PhpClass(
        override val name: String,
        override val extension: String,
        val parent: String? = null,
        val interfaces: List<String> = emptyList(),
        val isAbstract: Boolean = false,
        val isFinal: Boolean = false,
    ) : StubRecord()

    /** Global constant. */
    data class Constant(
        override val name: String,
        override val extension: String,
        val type: PhpType,
        val value: String,
    ) : StubRecord()

    /** Class constant. */
    data class ClassConstant(
        override val name: String,
        override val extension: String,
        val owningClass: String,
        val type: PhpType,
        val value: String,
        val visibility: Visibility = Visibility.PUBLIC,
    ) : StubRecord()

    /** Class property. */
    data class Property(
        override val name: String,
        override val extension: String,
        val owningClass: String,
        val type: PhpType = PhpType.MIXED,
        val visibility: Visibility = Visibility.PUBLIC,
        val isStatic: Boolean = false,
    ) : StubRecord()
}
