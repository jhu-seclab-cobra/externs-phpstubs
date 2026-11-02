package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.OperationSubject
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.VulnTypeId
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/** The operation fact is loaded, vocabulary-mapped and merged without changing wrapper arguments. */
internal class DynamicInvocationFactTest {
    @Test
    fun `dynamic invocation has its own selector sink`() {
        val operation = assertNotNull(PhpStubs.record(OperationSubject.DYNAMIC_INVOCATION))
        val sink = operation.sinkFacts.single()
        assertEquals(OperationSubject.DYNAMIC_INVOCATION, sink.owner)
        assertEquals(Port.Callee, sink.port)
        assertEquals(VulnTypeId("callablei"), sink.vulnType)
        assertTrue(PhpStubs.sinkFacts.contains(sink))
    }

    @Test
    fun `wrappers retain their argument facts`() {
        listOf("call_user_func", "call_user_func_array").forEach { wrapper ->
            val sinks = assertNotNull(PhpStubs.function(wrapper)).sinkFacts
            assertTrue(sinks.any { it.port == Port.Argument(0) && it.vulnType == VulnTypeId("callablei") })
            assertTrue(sinks.all { it.port is Port.Argument })
        }
    }
}
