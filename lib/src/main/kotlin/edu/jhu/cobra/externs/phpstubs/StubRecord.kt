package edu.jhu.cobra.externs.phpstubs

/**
 * Immutable record representing a PHP built-in entity from PhpStorm stubs.
 *
 * @property name The normalized name of the entity (e.g., "strlen", "pdo::query").
 * @property extension The PHP extension this entity belongs to (e.g., "standard", "Core", "pdo").
 */
data class StubRecord(
    val name: String,
    val extension: String,
)
