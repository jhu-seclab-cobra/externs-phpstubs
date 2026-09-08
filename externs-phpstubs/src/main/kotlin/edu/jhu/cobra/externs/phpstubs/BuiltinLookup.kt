package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.PropertySubject
import edu.jhu.cobra.commons.phpmodels.TaintPolicy
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import edu.jhu.cobra.commons.phpmodels.Vocabulary

/**
 * The read surface of one merge of document sets: exact lookup per declaration kind, enumeration per
 * declaration kind and per fact kind, and the accumulated vocabulary and policy.
 *
 * Every exact lookup spells its subject in PHP's own grammar (`substr`, `mysqli::query`, `PDO::ATTR_ERRMODE`,
 * `mysqli::$insert_id`, `$_GET`); a name that is not a spelling of the kind is the format library's
 * [IllegalArgumentException], and an absent subject is null. No suffix, prefix, or case-folded index
 * exists: a looser match is the consumer's filter over an enumeration.
 */
public interface BuiltinLookup {
    /** The record of the function spelled [name], or null. */
    public fun function(name: String): BuiltinRecord<FunctionSubject>?

    /** The record of the class spelled [name], or null. */
    public fun clazz(name: String): BuiltinRecord<ClassSubject>?

    /** The record of the method spelled `Owner::name`, or null. */
    public fun method(spelling: String): BuiltinRecord<MethodSubject>?

    /** The record of the method [name] of class [owner], or null. */
    public fun method(
        owner: String,
        name: String,
    ): BuiltinRecord<MethodSubject>?

    /** The record of the global constant spelled [name], case preserved, or null. */
    public fun constant(name: String): BuiltinRecord<ConstantSubject>?

    /** The record of the class constant spelled `Owner::NAME`, or null. */
    public fun classConstant(spelling: String): BuiltinRecord<ClassConstantSubject>?

    /** The record of the class constant [name] of class [owner], or null. */
    public fun classConstant(
        owner: String,
        name: String,
    ): BuiltinRecord<ClassConstantSubject>?

    /** The record of the property spelled `Owner::$name`, or null. */
    public fun property(spelling: String): BuiltinRecord<PropertySubject>?

    /** The record of the property [name] of class [owner], or null. */
    public fun property(
        owner: String,
        name: String,
    ): BuiltinRecord<PropertySubject>?

    /** The record of the predefined variable spelled `$name`, or null. */
    public fun variable(name: String): BuiltinRecord<VariableSubject>?

    /** The record of an already built [subject], or null. */
    public fun record(subject: ModelSubject): BuiltinRecord<ModelSubject>?

    /** Every function record, in first-statement order. */
    public val functions: Collection<BuiltinRecord<FunctionSubject>>

    /** Every class record, in first-statement order. */
    public val classes: Collection<BuiltinRecord<ClassSubject>>

    /** Every method record, in first-statement order. */
    public val methods: Collection<BuiltinRecord<MethodSubject>>

    /** Every global constant record, in first-statement order. */
    public val constants: Collection<BuiltinRecord<ConstantSubject>>

    /** Every class constant record, in first-statement order. */
    public val classConstants: Collection<BuiltinRecord<ClassConstantSubject>>

    /** Every property record, in first-statement order. */
    public val properties: Collection<BuiltinRecord<PropertySubject>>

    /** Every predefined variable record, in first-statement order. */
    public val variables: Collection<BuiltinRecord<VariableSubject>>

    /** Every sink fact over every record, in record then statement order. */
    public val sinks: List<SinkFact>

    /** Every source fact over every record, in record then statement order. */
    public val sources: List<SourceFact>

    /** Every sanitizer fact over every record, in record then statement order. */
    public val sanitizers: List<SanitizerFact>

    /** Every flow fact over every record, in record then statement order. */
    public val flows: List<FlowFact>

    /** Every returns fact over every record, in record then statement order. */
    public val returns: List<ReturnsFact>

    /** The vocabulary accumulated over every mounted set. */
    public val vocabulary: Vocabulary

    /** The taint policy accumulated over every mounted set. */
    public val policy: TaintPolicy
}
