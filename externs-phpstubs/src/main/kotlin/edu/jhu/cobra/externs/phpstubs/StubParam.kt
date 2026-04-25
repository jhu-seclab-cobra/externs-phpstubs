package edu.jhu.cobra.externs.phpstubs

/**
 * Typed parameter descriptor for a PHP function.
 *
 * @property name Parameter name.
 * @property type Parameter type.
 * @property optional True if the parameter has a default value.
 * @property defaultValue String representation of the default value. Null if no default. Consumer converts to domain types.
 */
data class StubParam(
    val name: String,
    val type: PhpType,
    val optional: Boolean = false,
    val defaultValue: String? = null,
) {
    init {
        if (!optional) require(defaultValue == null) { "non-optional param cannot have defaultValue" }
    }
}
