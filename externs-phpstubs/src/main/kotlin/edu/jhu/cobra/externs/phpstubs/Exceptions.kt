package edu.jhu.cobra.externs.phpstubs

/**
 * Thrown when a stub resource (index file or stub YAML file) cannot be found or loaded.
 *
 * @param resource The resource path that failed to load.
 */
public class StubIndexNotFoundException(
    resource: String,
) : RuntimeException("Stub resource not found: $resource")

/**
 * Thrown when a stub index file has an invalid or corrupted format.
 *
 * @param reason Description of the format violation.
 * @param cause Underlying parser error, or null when the violation is detected directly.
 */
public class StubIndexInvalidException(
    reason: String,
    cause: Throwable? = null,
) : RuntimeException("Stub index is invalid: $reason", cause)
