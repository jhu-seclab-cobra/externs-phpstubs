package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ArgPattern
import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelEntry
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.PolicyRow
import edu.jhu.cobra.commons.phpmodels.Precedence
import edu.jhu.cobra.commons.phpmodels.PropertySubject
import edu.jhu.cobra.commons.phpmodels.TaintPolicy
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import edu.jhu.cobra.commons.phpmodels.Vocabulary
import java.util.EnumMap

/** The five override units one entry can state; a statement is replaced whole per unit. */
internal enum class OverrideUnit { SIGNATURE, VALUE, SOURCES, SINKS, SANITIZERS }

/** One entry as mounted: its set's position and verification rank, and its extension when derived. */
private data class Mounted(
    val position: Int,
    val rank: Int,
    val entry: ModelEntry,
    val extension: String?,
)

/** The entry whose unit is in force for one (subject, condition, unit) key, with its extension. */
private data class Statement(
    val entry: ModelEntry,
    val extension: String?,
)

private typealias Slots = LinkedHashMap<ArgPattern?, EnumMap<OverrideUnit, Statement>>

/**
 * The fold of every mount into one statement per (subject, condition, unit) key, and the records built
 * from it. Built once per mount sequence and immutable: one map per declaration kind in first-statement
 * order, and the five fact lists in record order.
 */
internal class Merge private constructor(
    val vocabulary: Vocabulary,
    val policy: TaintPolicy,
) {
    private val all = LinkedHashMap<ModelSubject, BuiltinRecord<ModelSubject>>()
    val functions = LinkedHashMap<FunctionSubject, BuiltinRecord<FunctionSubject>>()
    val classes = LinkedHashMap<ClassSubject, BuiltinRecord<ClassSubject>>()
    val methods = LinkedHashMap<MethodSubject, BuiltinRecord<MethodSubject>>()
    val constants = LinkedHashMap<ConstantSubject, BuiltinRecord<ConstantSubject>>()
    val classConstants = LinkedHashMap<ClassConstantSubject, BuiltinRecord<ClassConstantSubject>>()
    val properties = LinkedHashMap<PropertySubject, BuiltinRecord<PropertySubject>>()
    val variables = LinkedHashMap<VariableSubject, BuiltinRecord<VariableSubject>>()

    val records: Map<ModelSubject, BuiltinRecord<ModelSubject>> get() = all

    val sinks: List<SinkFact> by lazy { all.values.flatMap { it.sinks } }
    val sources: List<SourceFact> by lazy { all.values.flatMap { it.sources } }
    val sanitizers: List<SanitizerFact> by lazy { all.values.flatMap { it.sanitizers } }
    val flows: List<FlowFact> by lazy { all.values.flatMap { it.flows } }
    val returns: List<ReturnsFact> by lazy { all.values.flatMap { it.returns } }

    // Builds the record once per subject and stores it under its own kind and under the shared map.
    private fun add(
        subject: ModelSubject,
        slots: Slots,
    ) {
        when (subject) {
            is FunctionSubject -> functions[subject] = record(subject, slots)
            is ClassSubject -> classes[subject] = record(subject, slots)
            is MethodSubject -> methods[subject] = record(subject, slots)
            is ConstantSubject -> constants[subject] = record(subject, slots)
            is ClassConstantSubject -> classConstants[subject] = record(subject, slots)
            is PropertySubject -> properties[subject] = record(subject, slots)
            is VariableSubject -> variables[subject] = record(subject, slots)
        }
    }

    // Assembles one record: the unconditional signature, then every fact of every statement per condition.
    private fun <S : ModelSubject> record(
        subject: S,
        slots: Slots,
    ): BuiltinRecord<S> {
        val signed = slots[null]?.get(OverrideUnit.SIGNATURE)
        val facts = FactLists()
        for ((condition, units) in slots) {
            for ((unit, statement) in units) facts.add(subject, condition, unit, statement.entry)
        }
        val record =
            BuiltinRecord(
                subject = subject,
                extension = signed?.extension,
                signature = signed?.entry?.signature,
                returns = facts.returns,
                flows = facts.flows,
                sources = facts.sources,
                sinks = facts.sinks,
                sanitizers = facts.sanitizers,
            )
        all[subject] = record
        return record
    }

    private class FactLists {
        val returns = ArrayList<ReturnsFact>()
        val flows = ArrayList<FlowFact>()
        val sources = ArrayList<SourceFact>()
        val sinks = ArrayList<SinkFact>()
        val sanitizers = ArrayList<SanitizerFact>()

        fun add(
            owner: ModelSubject,
            condition: ArgPattern?,
            unit: OverrideUnit,
            entry: ModelEntry,
        ) {
            val body = entry.body
            when (unit) {
                OverrideUnit.SIGNATURE -> Unit
                OverrideUnit.VALUE -> {
                    returns += ReturnsFact(owner, condition, body.returns!!)
                    body.propagation.orEmpty().mapTo(flows) { FlowFact(owner, condition, it.from, it.to) }
                }
                OverrideUnit.SOURCES ->
                    body.sources.orEmpty().mapTo(sources) { SourceFact(owner, condition, it.origin, it.at, it.keys) }
                OverrideUnit.SINKS -> body.sinks.orEmpty().mapTo(sinks) { SinkFact(owner, condition, it.port, it.vulnClass) }
                OverrideUnit.SANITIZERS ->
                    body.sanitizers.orEmpty().mapTo(sanitizers) { SanitizerFact(owner, condition, it.categories) }
            }
        }
    }

    companion object {
        /**
         * Folds [mounts] in position order under [precedence]: per key the highest-ranked statement is in
         * force and, among equal ranks, the later mounted. A conditional entry declaring a signature is
         * [StubIndexInvalidException].
         */
        fun of(
            mounts: List<Mount>,
            precedence: Precedence = Precedence.DEFAULT,
        ): Merge {
            var vocabulary = Vocabulary.EMPTY
            val rows = ArrayList<PolicyRow>()
            val mounted = ArrayList<Mounted>()
            for (mount in mounts) {
                vocabulary = vocabulary.merge(mount.vocabulary)
                rows += mount.policy
                val rank = precedence.rank(mount.verification)
                mount.entries.mapTo(mounted) { (entry, extension) -> Mounted(mount.position, rank, entry, extension) }
            }
            val merge = Merge(vocabulary, TaintPolicy(rows))
            for ((subject, slots) in fold(mounted)) merge.add(subject, slots)
            return merge
        }

        // Subjects and conditions keep first-statement order; statements are written weakest first so the last write wins.
        private fun fold(mounted: List<Mounted>): Map<ModelSubject, Slots> {
            val statements = LinkedHashMap<ModelSubject, Slots>()
            for (item in mounted) {
                val entry = item.entry
                if (entry.condition != null && entry.signature != null) {
                    throw StubIndexInvalidException("Conditional entry for '${entry.subject}' declares a signature")
                }
                statements.getOrPut(entry.subject) { Slots() }.getOrPut(entry.condition) { EnumMap(OverrideUnit::class.java) }
            }
            val weakestFirst = compareByDescending<Mounted> { it.rank }.thenBy { it.position }
            for (item in mounted.sortedWith(weakestFirst)) {
                val slots = statements.getValue(item.entry.subject).getValue(item.entry.condition)
                for (unit in declaredUnits(item.entry)) slots[unit] = Statement(item.entry, item.extension)
            }
            return statements
        }

        private fun declaredUnits(entry: ModelEntry): List<OverrideUnit> =
            listOfNotNull(
                OverrideUnit.SIGNATURE.takeIf { entry.signature != null },
                OverrideUnit.VALUE.takeIf { entry.body.returns != null },
                OverrideUnit.SOURCES.takeIf { entry.body.sources != null },
                OverrideUnit.SINKS.takeIf { entry.body.sinks != null },
                OverrideUnit.SANITIZERS.takeIf { entry.body.sanitizers != null },
            )
    }
}
