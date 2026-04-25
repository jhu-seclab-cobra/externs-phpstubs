package edu.jhu.cobra.externs.phpstubs

/**
 * PHP type system representation. Framework-independent — no analysis tool dependencies.
 * Consumers convert at the boundary (e.g., `PhpType.STRING` to their domain string type).
 */
enum class PhpType {
    STRING,
    INT,
    FLOAT,
    BOOL,
    ARRAY,
    OBJECT,
    MIXED,
    VOID,
    NULL,
    CALLABLE,
    RESOURCE,
}
