package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.PropertySubject
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.CallableSignature
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.ClassSignature
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.PropertySignature
import edu.jhu.cobra.commons.phpmodels.SignatureInfo.TypedSignature
import edu.jhu.cobra.commons.phpmodels.SubjectModel

/**
 * One registry entry: a decoded model together with its extension provenance.
 *
 * @param S The subject kind, so a lookup result exposes its identity fields without a cast.
 * @property subject The declaration the model identifies; equal to `model.subject`.
 * @property model The decoded model entry as commons-phpmodels validated it.
 * @property extension The PHP extension providing the declaration, derived from the document's file name.
 * @throws IllegalArgumentException If [subject] differs from the model's subject or [extension] is blank.
 */
public data class StubEntry<out S : ModelSubject>(
    val subject: S,
    val model: SubjectModel,
    val extension: String,
) {
    init {
        require(model.subject == subject) { "Entry subject '$subject' does not match model subject '${model.subject}'" }
        require(extension.isNotBlank()) { "Entry '$subject' has a blank extension" }
    }
}

/** The callable signature of a function entry. Present on every registry entry by the loader's corpus rules. */
public val StubEntry<FunctionSubject>.callableSignature: CallableSignature
    @JvmName("functionCallableSignature")
    get() = model.signature as CallableSignature

/** The callable signature of a method entry. */
public val StubEntry<MethodSubject>.callableSignature: CallableSignature
    @JvmName("methodCallableSignature")
    get() = model.signature as CallableSignature

/** The class signature of a class entry. */
public val StubEntry<ClassSubject>.classSignature: ClassSignature
    get() = model.signature as ClassSignature

/** The typed signature of a global constant entry. */
public val StubEntry<ConstantSubject>.typedSignature: TypedSignature
    @JvmName("constantTypedSignature")
    get() = model.signature as TypedSignature

/** The typed signature of a class constant entry. */
public val StubEntry<ClassConstantSubject>.typedSignature: TypedSignature
    @JvmName("classConstantTypedSignature")
    get() = model.signature as TypedSignature

/** The property signature of a property entry. */
public val StubEntry<PropertySubject>.propertySignature: PropertySignature
    get() = model.signature as PropertySignature
