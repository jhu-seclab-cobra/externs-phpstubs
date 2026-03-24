package edu.jhu.cobra.externs.phpstubs

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class StubSectionTest {

    @Test
    fun `EMPTY section contains nothing`() {
        assertFalse(StubSection.EMPTY.contains("anything"))
        assertNull(StubSection.EMPTY.get("anything"))
    }

    @Test
    fun `contains returns true for existing key`() {
        val section = StubSection(setOf("strlen"), mapOf("strlen" to byteArrayOf(0x01, 0x73, 0x74, 0x64))) // STR "std"
        assertTrue(section.contains("strlen"))
    }

    @Test
    fun `contains returns false for missing key`() {
        val section = StubSection(setOf("strlen"), mapOf("strlen" to byteArrayOf()))
        assertFalse(section.contains("unknown"))
    }

    @Test
    fun `get returns StubRecord with extracted extension for ListVal bytes`() {
        // Simulate a serialized ListVal("standard"):
        // 0x0C = LIST tag, then 4-byte element size (9), then 0x01 = STR tag, then "standard"
        val strBytes = "standard".toByteArray(Charsets.UTF_8)
        val elementSize = 1 + strBytes.size // STR tag + string bytes
        val bytes = byteArrayOf(
            0x0C, // LIST type
            (elementSize shr 24).toByte(), (elementSize shr 16).toByte(),
            (elementSize shr 8).toByte(), elementSize.toByte(),
            0x01, // STR type
        ) + strBytes

        val section = StubSection(setOf("strlen"), mapOf("strlen" to bytes))
        val record = section.get("strlen")
        assertNotNull(record)
        assertEquals("strlen", record.name)
        assertEquals("standard", record.extension)
    }

    @Test
    fun `get caches result and returns same instance`() {
        val bytes = byteArrayOf(0x01) + "Core".toByteArray(Charsets.UTF_8)
        val section = StubSection(setOf("define"), mapOf("define" to bytes))
        val first = section.get("define")
        val second = section.get("define")
        assertTrue(first === second, "Expected cached instance")
    }

    @Test
    fun `get returns null for missing key`() {
        val section = StubSection(setOf("strlen"), mapOf("strlen" to byteArrayOf()))
        assertNull(section.get("unknown"))
    }

    @Test
    fun `extractExtension handles STR type directly`() {
        val bytes = byteArrayOf(0x01) + "pdo".toByteArray(Charsets.UTF_8)
        assertEquals("pdo", StubSection.extractExtension(bytes))
    }

    @Test
    fun `extractExtension returns unknown for empty bytes`() {
        assertEquals("unknown", StubSection.extractExtension(byteArrayOf()))
    }

    @Test
    fun `extractExtension returns unknown for unrecognized type`() {
        assertEquals("unknown", StubSection.extractExtension(byteArrayOf(0x7F)))
    }
}
