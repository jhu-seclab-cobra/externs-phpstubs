package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ArgPattern
import edu.jhu.cobra.commons.phpmodels.KeyPattern
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.OriginId
import edu.jhu.cobra.commons.phpmodels.Port
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.VulnClassId

/**
 * One element of one assertion statement in force for a built-in, with the record it belongs to and the
 * condition it holds under. A consumer matches [condition] against its own call arguments through
 * [ArgPattern.matches] and applies its own rule to an undecidable outcome; the library ranks nothing.
 */
public sealed interface Fact {
    /** The subject of the record this fact was read from. */
    public val owner: ModelSubject

    /** The condition of the entry that stated this fact, or null for an unconditional statement. */
    public val condition: ArgPattern?
}

/** One dangerously consumed argument under one danger category. */
public data class SinkFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val port: Port.Argument,
    val vulnClass: VulnClassId,
) : Fact

/** One production of origin colors: at the result, or at an explicit by-reference argument site. */
public data class SourceFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val origins: Set<OriginId>,
    val at: Port.Argument?,
    val keys: List<KeyPattern>?,
) : Fact

/** The danger categories a call neutralizes. */
public data class SanitizerFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val categories: Set<VulnClassId>,
) : Fact

/** One declared flow from an input port to another port of the same call. */
public data class FlowFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val from: Port.Input,
    val to: Port,
) : Fact

/** The classification of a call's result. */
public data class ReturnsFact(
    override val owner: ModelSubject,
    override val condition: ArgPattern?,
    val kind: ReturnKind,
) : Fact
