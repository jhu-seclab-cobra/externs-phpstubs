package edu.jhu.cobra.externs.phpstubs

/**
 * Thrown when a stub index resource cannot be found or loaded.
 *
 * @param resource The resource path that failed to load.
 */
class StubIndexNotFoundException(resource: String) :
    RuntimeException("Stub index resource not found: $resource")

/**
 * Thrown when a stub index file has an invalid or corrupted format.
 *
 * @param reason Description of the format violation.
 */
class StubIndexInvalidException(reason: String) :
    RuntimeException("Stub index is invalid: $reason")
