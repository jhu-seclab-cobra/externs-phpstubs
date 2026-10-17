package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ArgPattern
import edu.jhu.cobra.commons.phpmodels.ArgumentCheck
import edu.jhu.cobra.commons.phpmodels.CharacterBound
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.KeyPattern
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.SourceKindId
import edu.jhu.cobra.commons.phpmodels.VulnTypeId

/**
 * One element of one assertion unit of an entry in force for a builtin, with the record it belongs to and the
 * condition it holds under. A consumer matches [condition] against its own call arguments through
 * [ArgPattern.matches] and applies its own rule to an undecidable outcome; the library ranks nothing.
 */
public sealed interface Fact {
    /** The subject of the record this fact was read from. */
    public val owner: ModelSubject

    /** The condition of the entry that stated this fact, or null for an unconditional entry. */
    public val condition: ArgPattern?
}

/** One dangerously consumed argument under one vulnerability type. */
public data class SinkFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val port: Port.Argument,
    val vulnType: VulnTypeId,
) : Fact

/** One production of source kinds: at the result, or at an explicit by-reference argument site. */
public data class SourceFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val sourceKinds: Set<SourceKindId>,
    val at: Port.Argument?,
    val keys: List<KeyPattern>?,
) : Fact

/**
 * The vulnerability types a call neutralizes: in its result, or, with a [check], in the argument a call
 * returning the accepting value accepted. The check also carries the class or type set of that argument.
 */
public data class SanitizerFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val vulnTypes: Set<VulnTypeId>,
    val check: ArgumentCheck?,
) : Fact

/** One declared flow from an input port to another port of the same call. */
public data class FlowFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val from: Port.Input,
    val to: Port,
) : Fact

/** The return kind of a call's result. */
public data class ReturnsFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val kind: ReturnKind,
) : Fact

/**
 * The bytes a call's result may hold: every result byte is a byte of a [CharacterBound.of] port's value and a
 * member of [CharacterBound.within]; a null field of the bound states no bound of its kind.
 */
public data class CharactersFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val bound: CharacterBound,
) : Fact

/** The exception classes a call may throw; the empty set states it throws none. */
public data class ThrowsFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val classes: Set<ClassSubject>,
) : Fact
