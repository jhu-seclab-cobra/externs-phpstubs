package edu.jhu.cobra.externs.phpstubs

/**
 * Typed parameter descriptor for a PHP function.
 *
 * @property optional True if the parameter has a default value.
 * @property defaultValue Default value string, or null if none.
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
