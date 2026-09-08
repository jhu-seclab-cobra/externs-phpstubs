package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.PropertySubject
import edu.jhu.cobra.commons.phpmodels.SignatureInfo
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.CallableSignature
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.ClassSignature
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.PropertySignature
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.TypedSignature

/**
 * The one thing a consumer reads about a built-in: its subject, the PHP extension of its declaration,
 * the signature in force, and every fact in force under every condition.
 *
 * @param S The subject kind, so a lookup result exposes its identity fields without a cast.
 * @property subject The declaration the record identifies.
 * @property extension The PHP extension of the generated declaration, or null when no generated set declares it.
 * @property signature The unconditional signature statement in force, or null for a fact-only record.
 * @property returns Every returns fact, in statement order.
 * @property flows Every flow fact, in statement order.
 * @property sources Every source fact, in statement order.
 * @property sinks Every sink fact, in statement order.
 * @property sanitizers Every sanitizer fact, in statement order.
 * @throws IllegalArgumentException If a fact names another owner or the record asserts nothing.
 */
public data class BuiltinRecord<out S : ModelSubject>(
    val subject: S,
    val extension: String?,
    val signature: SignatureInfo?,
    val returns: List<ReturnsFact>,
    val flows: List<FlowFact>,
    val sources: List<SourceFact>,
    val sinks: List<SinkFact>,
    val sanitizers: List<SanitizerFact>,
) {
    /** Every fact of the record: returns, flows, sources, sinks, then sanitizers. */
    val facts: List<Fact>
        get() = returns + flows + sources + sinks + sanitizers

    init {
        val declared = facts
        val foreign = declared.firstOrNull { it.owner != subject }
        require(foreign == null) { "Record '$subject' holds a fact owned by '${foreign?.owner}'" }
        require(signature != null || declared.isNotEmpty()) { "Record '$subject' declares neither a signature nor a fact" }
    }
}

/** The callable signature of a function record, or null when no set declares one. */
public val BuiltinRecord<FunctionSubject>.callableSignature: CallableSignature?
    @JvmName("functionCallableSignature")
    get() = signature as CallableSignature?

/** The callable signature of a method record, or null when no set declares one. */
public val BuiltinRecord<MethodSubject>.callableSignature: CallableSignature?
    @JvmName("methodCallableSignature")
    get() = signature as CallableSignature?

/** The class signature of a class record, or null when no set declares one. */
public val BuiltinRecord<ClassSubject>.classSignature: ClassSignature?
    get() = signature as ClassSignature?

/** The typed signature of a global constant record, or null when no set declares one. */
public val BuiltinRecord<ConstantSubject>.typedSignature: TypedSignature?
    @JvmName("constantTypedSignature")
    get() = signature as TypedSignature?

/** The typed signature of a class constant record, or null when no set declares one. */
public val BuiltinRecord<ClassConstantSubject>.typedSignature: TypedSignature?
    @JvmName("classConstantTypedSignature")
    get() = signature as TypedSignature?

/** The property signature of a property record, or null when no set declares one. */
public val BuiltinRecord<PropertySubject>.propertySignature: PropertySignature?
    get() = signature as PropertySignature?
