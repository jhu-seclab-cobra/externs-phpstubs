package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.NamedExtras
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.CallableSignature
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull

/**
 * Named-extra facts loaded through the bundled models and ordinary signature merge.
 *
 * - `array_map rejects before its first array reception` — k comes from argument parsing.
 * - `call_user_func forwards extra names` — the callback receives the names.
 * - `method forwarders retain extra names` — Closure, Reflection and Fiber signatures agree with PHP.
 * - `imagefilter keeps unextracted accept and ignore behavior` — no inferred rejection.
 * - `ordinary builtin parameters have no policy` — no blanket builtin fact.
 */
internal class BuiltinNamedExtrasTest {
    @Test
    fun `array_map rejects before its first array reception`() {
        assertEquals(NamedExtras.Reject(1), policy(function("array_map")))
    }

    @Test
    fun `call_user_func forwards extra names`() {
        assertEquals(NamedExtras.Forward, policy(function("call_user_func")))
    }

    @Test
    fun `method forwarders retain extra names`() {
        val methods =
            listOf(
                "Closure" to "call",
                "ReflectionFunction" to "invoke",
                "ReflectionMethod" to "invoke",
                "ReflectionClass" to "newInstance",
                "Fiber" to "start",
            )
        for ((owner, name) in methods) {
            val signature = assertNotNull(PhpStubs.method(owner, name)).callableSignature
            assertEquals(NamedExtras.Forward, policy(assertNotNull(signature)), "$owner::$name")
        }
    }

    @Test
    fun `imagefilter keeps unextracted accept and ignore behavior`() {
        assertNull(policy(function("imagefilter")))
    }

    @Test
    fun `ordinary builtin parameters have no policy`() {
        assertEquals(listOf(null), function("strlen").params.map { it.namedExtras })
    }

    private fun function(name: String): CallableSignature =
        assertNotNull(assertNotNull(PhpStubs.function(name)).callableSignature)

    private fun policy(signature: CallableSignature): NamedExtras? =
        signature.params.single { it.variadic }.namedExtras
}
