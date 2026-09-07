package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.Propagation
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.ValueSemantics
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull

/**
 * Tests for the hand-declared documents under `models/manual/`: built-ins the extraction does not produce.
 *
 * - `manual documents declare the query methods the extraction omits` — verifies the seven methods carry their
 *   owner's extension
 * - `manual documents declare functions outside the upstream release` — verifies PHP 8.3 and removed functions
 *   under `standard` and `mysql`
 * - `manual declarations carry the reviewed value unit` — verifies typed results and query flows
 * - `create_function declares existence without a flow set` — verifies the entry without propagation has no unit
 */
internal class ManualDeclarationsTest {
    private val registry by lazy { StubLoader.loadAll() }

    @Test
    fun `manual documents declare the query methods the extraction omits`() {
        val expected =
            mapOf(
                MethodSubject("mysqli", "query") to "mysqli",
                MethodSubject("mysqli", "multi_query") to "mysqli",
                MethodSubject("mysqli", "real_query") to "mysqli",
                MethodSubject("PDO", "query") to "pdo",
                MethodSubject("PDO", "exec") to "pdo",
                MethodSubject("SQLite3", "query") to "sqlite3",
                MethodSubject("SQLite3", "exec") to "sqlite3",
            )
        for ((subject, extension) in expected) {
            assertEquals(extension, assertNotNull(registry.methods[subject], "$subject").extension, "$subject")
        }
    }

    @Test
    fun `manual documents declare functions outside the upstream release`() {
        val standard = listOf("str_decrement", "str_increment", "hebrevc", "convert_cyr_string", "money_format", "each")
        for (name in standard) {
            assertEquals("standard", assertNotNull(registry.functions[FunctionSubject(name)], name).extension, name)
        }
        assertEquals("mysql", assertNotNull(registry.functions[FunctionSubject("mysql_query")]).extension)
    }

    @Test
    fun `manual declarations carry the reviewed value unit`() {
        assertEquals(ValueSemantics(ReturnKind.ANY, listOf(argumentToReturn(0))), unitOf(MethodSubject("mysqli", "query")))
        assertEquals(ValueSemantics(ReturnKind.BOOL, listOf(argumentToReturn(0))), unitOf(MethodSubject("mysqli", "multi_query")))
        assertEquals(ValueSemantics(ReturnKind.BOOL, listOf(argumentToReturn(0))), unitOf(MethodSubject("SQLite3", "exec")))
        assertEquals(ValueSemantics(ReturnKind.STR, listOf(argumentToReturn(0))), unitOf(FunctionSubject("str_increment")))
        assertEquals(
            ValueSemantics(ReturnKind.STR, listOf(argumentToReturn(0), argumentToReturn(1))),
            unitOf(FunctionSubject("money_format")),
        )
    }

    @Test
    fun `create_function declares existence without a flow set`() {
        assertNull(unitOf(FunctionSubject("create_function")))
    }

    private fun unitOf(subject: ModelSubject): ValueSemantics? =
        (registry.functions[subject] ?: registry.methods[subject])!!.model.body.valueSemantics()

    private fun argumentToReturn(position: Int): Propagation = Propagation(from = Port.Argument(position), to = Port.Return)
}
