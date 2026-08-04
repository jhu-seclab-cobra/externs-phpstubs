package edu.jhu.cobra.externs.phpstubs

/** Strips one leading `/` or `\` namespace separator. For case-sensitive keys (constants). */
internal fun String.stripLeadingSlash(): String = if (startsWith('/') || startsWith('\\')) substring(1) else this

/**
 * Strips one leading slash and lowercases. For case-insensitive keys (functions, classes, methods, properties).
 * Shared by [StubLoader] key construction and [PhpStubs] lookup so stored keys and query keys always match.
 */
internal fun String.normalizeStubKey(): String = stripLeadingSlash().lowercase()
