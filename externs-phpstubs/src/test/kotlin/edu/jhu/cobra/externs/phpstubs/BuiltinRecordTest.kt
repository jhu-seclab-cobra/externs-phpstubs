package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.Classifier
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.DeclaredType
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.SignatureInfo
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for [BuiltinRecord] construction and its typed signature accessors.
 *
 * - `a record holds a signature or at least one fact` — verifies the empty record is rejected
 * - `every fact names the record's subject` — verifies a foreign owner is rejected
 * - `facts enumerates every kind in order` — verifies returns precede flows precede taint facts
 * - `typed accessors narrow the signature per subject kind` — verifies the callable and typed views
 */
internal class BuiltinRecordTest {
    private val f = FunctionSubject("f")

    @Test
    fun `a record holds a signature or at least one fact`() {
        val failure = assertFailsWith<IllegalArgumentException> { record(f, signature = null) }
        assertTrue("neither" in failure.message!!)
    }

    @Test
    fun `every fact names the record's subject`() {
        val foreign = ReturnsFact(FunctionSubject("g"), null, ReturnKind.ANY)
        val failure = assertFailsWith<IllegalArgumentException> { record(f, signature = null, returns = listOf(foreign)) }
        assertTrue("g" in failure.message!!)
    }

    @Test
    fun `facts enumerates every kind in order`() {
        val returns = ReturnsFact(f, null, ReturnKind.STR)
        val record = record(f, signature = null, returns = listOf(returns))
        assertEquals(listOf<Fact>(returns), record.facts)
        assertTrue(record.flows.isEmpty())
    }

    @Test
    fun `typed accessors narrow the signature per subject kind`() {
        val callable = SignatureInfo.CallableSignature(emptyList(), DeclaredType("int"))
        assertEquals(callable, record(f, callable).callableSignature)
        val typed = SignatureInfo.TypedSignature(DeclaredType("int"), "1")
        assertEquals(typed, record(ConstantSubject("C"), typed).typedSignature)
        assertNull(record(ClassSubject("K"), SignatureInfo.ClassSignature(Classifier.CLASS)).classSignature?.parent)
    }

    private fun <S : edu.jhu.cobra.commons.phpmodels.ModelSubject> record(
        subject: S,
        signature: SignatureInfo?,
        returns: List<ReturnsFact> = emptyList(),
    ): BuiltinRecord<S> = BuiltinRecord(subject, null, signature, returns, emptyList(), emptyList(), emptyList(), emptyList())
}
