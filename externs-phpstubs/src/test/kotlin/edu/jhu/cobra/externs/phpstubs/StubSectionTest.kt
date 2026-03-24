package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.value.ListVal
import edu.jhu.cobra.commons.value.MapVal
import edu.jhu.cobra.commons.value.StrVal
import edu.jhu.cobra.commons.value.serializer.DftByteArraySerializerImpl
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class StubSectionTest {

    private fun serialize(value: edu.jhu.cobra.commons.value.IValue): ByteArray =
        DftByteArraySerializerImpl.serialize(value)

    @Test
    fun `EMPTY section contains nothing`() {
        assertFalse(StubSection.EMPTY.contains("anything"))
        assertNull(StubSection.EMPTY.get("anything"))
    }

    @Test
    fun `contains returns true for existing key`() {
        val bytes = serialize(ListVal(StrVal("standard")))
        val section = StubSection(setOf("strlen"), mapOf("strlen" to bytes))
        assertTrue(section.contains("strlen"))
    }

    @Test
    fun `contains returns false for missing key`() {
        val bytes = serialize(ListVal(StrVal("standard")))
        val section = StubSection(setOf("strlen"), mapOf("strlen" to bytes))
        assertFalse(section.contains("unknown"))
    }

    @Test
    fun `get returns StubRecord with extension from ListVal`() {
        val bytes = serialize(ListVal(StrVal("standard")))
        val section = StubSection(setOf("strlen"), mapOf("strlen" to bytes))
        val record = section.get("strlen")
        assertNotNull(record)
        assertEquals("strlen", record.name)
        assertEquals("standard", record.extension)
        assertTrue(record.value is ListVal)
    }

    @Test
    fun `get returns StubRecord with extension from StrVal`() {
        val bytes = serialize(StrVal("pdo"))
        val section = StubSection(setOf("define"), mapOf("define" to bytes))
        val record = section.get("define")
        assertNotNull(record)
        assertEquals("pdo", record.extension)
        assertTrue(record.value is StrVal)
    }

    @Test
    fun `get returns unknown extension for MapVal`() {
        val mapVal = MapVal(hashMapOf("key" to StrVal("val")))
        val bytes = serialize(mapVal)
        val section = StubSection(setOf("some_const"), mapOf("some_const" to bytes))
        val record = section.get("some_const")
        assertNotNull(record)
        assertEquals("unknown", record.extension)
    }

    @Test
    fun `get caches result and returns same instance`() {
        val bytes = serialize(ListVal(StrVal("Core")))
        val section = StubSection(setOf("define"), mapOf("define" to bytes))
        val first = section.get("define")
        val second = section.get("define")
        assertTrue(first === second, "Expected cached instance")
    }

    @Test
    fun `get returns null for missing key`() {
        val bytes = serialize(StrVal("std"))
        val section = StubSection(setOf("strlen"), mapOf("strlen" to bytes))
        assertNull(section.get("unknown"))
    }

    @Test
    fun `extractExtension handles ListVal`() {
        val value = ListVal(StrVal("standard"), StrVal("extra"))
        assertEquals("standard", StubSection.extractExtension(value))
    }

    @Test
    fun `extractExtension handles StrVal`() {
        assertEquals("pdo", StubSection.extractExtension(StrVal("pdo")))
    }

    @Test
    fun `extractExtension returns unknown for other types`() {
        val mapVal = MapVal(hashMapOf("k" to StrVal("v")))
        assertEquals("unknown", StubSection.extractExtension(mapVal))
    }
}
