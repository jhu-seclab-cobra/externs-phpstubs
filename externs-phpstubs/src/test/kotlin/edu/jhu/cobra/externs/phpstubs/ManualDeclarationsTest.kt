package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for the hand-declared documents under `models/manual/`: built-ins php-src 8.5.11 does not declare.
 *
 * - `manual documents declare functions removed before PHP 8` — verifies the removed functions under `standard`
 *   and `mysql`
 * - `manual declarations carry the reviewed value unit` — verifies the typed result and flows of `money_format`
 * - `create_function declares existence without a value unit` — verifies the entry without propagation
 */
internal class ManualDeclarationsTest {
    @Test
    fun `manual documents declare functions removed before PHP 8`() {
        for (name in listOf("hebrevc", "convert_cyr_string", "money_format", "each", "create_function")) {
            assertEquals("standard", assertNotNull(PhpStubs.function(name), name).extension, name)
        }
        assertEquals("mysql", assertNotNull(PhpStubs.function("mysql_query")).extension)
    }

    @Test
    fun `manual declarations carry the reviewed value unit`() {
        val record = assertNotNull(PhpStubs.function("money_format"))
        assertEquals(ReturnKind.STR, record.returns.single { it.condition == null }.kind)
        assertEquals(
            listOf(Port.Argument(0), Port.Argument(1)),
            record.flows.filter { it.condition == null && it.to == Port.Return }.map { it.from },
        )
    }

    @Test
    fun `create_function declares existence without a value unit`() {
        val record = assertNotNull(PhpStubs.function("create_function"))
        assertNotNull(record.signature)
        assertTrue(record.flows.isEmpty())
    }
}
