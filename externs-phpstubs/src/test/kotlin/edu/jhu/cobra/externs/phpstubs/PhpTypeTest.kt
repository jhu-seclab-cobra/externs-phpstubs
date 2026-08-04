package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull

/**
 * Tests for [PhpType] enum.
 *
 * - `enum has exactly 11 entries` -- design doc specifies 11 types.
 * - `STRING entry exists` -- valueOf resolves.
 * - `INT entry exists` -- valueOf resolves.
 * - `FLOAT entry exists` -- valueOf resolves.
 * - `BOOL entry exists` -- valueOf resolves.
 * - `ARRAY entry exists` -- valueOf resolves.
 * - `OBJECT entry exists` -- valueOf resolves.
 * - `MIXED entry exists` -- valueOf resolves.
 * - `VOID entry exists` -- valueOf resolves.
 * - `NULL entry exists` -- valueOf resolves.
 * - `CALLABLE entry exists` -- valueOf resolves.
 * - `RESOURCE entry exists` -- valueOf resolves.
 * - `valueOf works for all entries` -- round-trip name to enum.
 */
internal class PhpTypeTest {
    @Test
    fun `enum has exactly 11 entries`() {
        assertEquals(11, PhpType.entries.size)
    }

    @Test
    fun `STRING entry exists`() {
        assertNotNull(PhpType.valueOf("STRING"))
    }

    @Test
    fun `INT entry exists`() {
        assertNotNull(PhpType.valueOf("INT"))
    }

    @Test
    fun `FLOAT entry exists`() {
        assertNotNull(PhpType.valueOf("FLOAT"))
    }

    @Test
    fun `BOOL entry exists`() {
        assertNotNull(PhpType.valueOf("BOOL"))
    }

    @Test
    fun `ARRAY entry exists`() {
        assertNotNull(PhpType.valueOf("ARRAY"))
    }

    @Test
    fun `OBJECT entry exists`() {
        assertNotNull(PhpType.valueOf("OBJECT"))
    }

    @Test
    fun `MIXED entry exists`() {
        assertNotNull(PhpType.valueOf("MIXED"))
    }

    @Test
    fun `VOID entry exists`() {
        assertNotNull(PhpType.valueOf("VOID"))
    }

    @Test
    fun `NULL entry exists`() {
        assertNotNull(PhpType.valueOf("NULL"))
    }

    @Test
    fun `CALLABLE entry exists`() {
        assertNotNull(PhpType.valueOf("CALLABLE"))
    }

    @Test
    fun `RESOURCE entry exists`() {
        assertNotNull(PhpType.valueOf("RESOURCE"))
    }

    @Test
    fun `valueOf works for all entries`() {
        for (entry in PhpType.entries) {
            assertEquals(entry, PhpType.valueOf(entry.name))
        }
    }
}
