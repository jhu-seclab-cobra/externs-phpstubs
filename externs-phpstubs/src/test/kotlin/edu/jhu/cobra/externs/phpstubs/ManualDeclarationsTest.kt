package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for the hand-declared documents under `models/manual/`: built-ins the extraction does not produce.
 *
 * - `manual documents declare the query methods the extraction omits` — verifies the seven methods carry their
 *   owner's extension
 * - `manual documents declare functions outside the upstream release` — verifies PHP 8.3 and removed functions
 *   under `standard` and `mysql`
 * - `manual declarations carry the reviewed value unit` — verifies typed results and query flows
 * - `create_function declares existence without a value unit` — verifies the entry without propagation
 */
internal class ManualDeclarationsTest {
    @Test
    fun `manual documents declare the query methods the extraction omits`() {
        val expected =
            mapOf(
                "mysqli::query" to "mysqli",
                "mysqli::multi_query" to "mysqli",
                "mysqli::real_query" to "mysqli",
                "PDO::query" to "pdo",
                "PDO::exec" to "pdo",
                "SQLite3::query" to "sqlite3",
                "SQLite3::exec" to "sqlite3",
            )
        for ((spelling, extension) in expected) {
            assertEquals(extension, assertNotNull(PhpStubs.method(spelling), spelling).extension, spelling)
        }
    }

    @Test
    fun `manual documents declare functions outside the upstream release`() {
        val standard = listOf("str_decrement", "str_increment", "hebrevc", "convert_cyr_string", "money_format", "each")
        for (name in standard) {
            assertEquals("standard", assertNotNull(PhpStubs.function(name), name).extension, name)
        }
        assertEquals("mysql", assertNotNull(PhpStubs.function("mysql_query")).extension)
    }

    @Test
    fun `manual declarations carry the reviewed value unit`() {
        assertEquals(ReturnKind.ANY to listOf(0), unitOf(PhpStubs.method("mysqli::query")!!))
        assertEquals(ReturnKind.BOOL to listOf(0), unitOf(PhpStubs.method("mysqli::multi_query")!!))
        assertEquals(ReturnKind.BOOL to listOf(0), unitOf(PhpStubs.method("SQLite3::exec")!!))
        assertEquals(ReturnKind.STR to listOf(0), unitOf(PhpStubs.function("str_increment")!!))
        assertEquals(ReturnKind.STR to listOf(0, 1), unitOf(PhpStubs.function("money_format")!!))
    }

    @Test
    fun `create_function declares existence without a value unit`() {
        val record = assertNotNull(PhpStubs.function("create_function"))
        assertNotNull(record.signature)
        assertTrue(record.flows.isEmpty())
    }

    private fun unitOf(record: BuiltinRecord<*>): Pair<ReturnKind, List<Int>> =
        record.returns.single { it.condition == null }.kind to
            record.flows.filter { it.condition == null && it.to == Port.Return }.map { (it.from as Port.Argument).position }
}
