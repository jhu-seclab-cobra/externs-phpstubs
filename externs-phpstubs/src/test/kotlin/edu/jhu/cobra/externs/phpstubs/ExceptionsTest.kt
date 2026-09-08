package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertSame

/**
 * Tests for [StubIndexNotFoundException] and [StubIndexInvalidException].
 *
 * - `StubIndexNotFoundException message contains resource path` -- message format.
 * - `StubIndexNotFoundException extends RuntimeException` -- inheritance.
 * - `StubIndexInvalidException message contains reason` -- message format.
 * - `StubIndexInvalidException extends RuntimeException` -- inheritance.
 * - `StubIndexInvalidException attaches the format library's cause` -- cause chain.
 * - `StubIndexInvalidException cause is null when detected directly` -- default cause.
 */
internal class ExceptionsTest {
    @Test
    fun `StubIndexNotFoundException message contains resource path`() {
        val ex = StubIndexNotFoundException("/stubs/missing.yaml")
        assertEquals("Stub resource not found: /stubs/missing.yaml", ex.message)
    }

    @Test
    fun `StubIndexNotFoundException extends RuntimeException`() {
        val ex = StubIndexNotFoundException("test")
        assertIs<RuntimeException>(ex)
    }

    @Test
    fun `StubIndexInvalidException message contains reason`() {
        val ex = StubIndexInvalidException("unknown tag: foo")
        assertEquals("Stub index is invalid: unknown tag: foo", ex.message)
    }

    @Test
    fun `StubIndexInvalidException extends RuntimeException`() {
        val ex = StubIndexInvalidException("test")
        assertIs<RuntimeException>(ex)
    }

    @Test
    fun `StubIndexInvalidException attaches the format library's cause`() {
        val cause = IllegalArgumentException("malformed")
        assertSame(cause, StubIndexInvalidException("bad.yaml", cause).cause)
    }

    @Test
    fun `StubIndexInvalidException cause is null when detected directly`() {
        assertNull(StubIndexInvalidException("corpus rule").cause)
    }
}
