package edu.jhu.cobra.externs.phpstubs

/**
 * Immutable registry holding all parsed PHP stub records, categorized by entity type.
 *
 * @property functions Global PHP functions keyed by normalized name.
 * @property classes PHP classes keyed by normalized name.
 * @property methods Class methods keyed by "class::method" normalized name.
 * @property constants Global PHP constants keyed by normalized name.
 * @property classConstants Class constants keyed by "class::constant" normalized name.
 * @property properties Class properties keyed by "class::property" normalized name.
 */
data class StubRegistry(
    val functions: Map<String, StubRecord.Function>,
    val classes: Map<String, StubRecord.PhpClass>,
    val methods: Map<String, StubRecord.Method>,
    val constants: Map<String, StubRecord.Constant>,
    val classConstants: Map<String, StubRecord.ClassConstant>,
    val properties: Map<String, StubRecord.Property>,
)
