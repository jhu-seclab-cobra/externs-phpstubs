package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassSubject

/**
 * The class records of a class map in key order, each once: the entries whose key is the record's own
 * declaration subject. A view over [keyed]; it stores nothing, so the alias keys of the map never list a record twice.
 */
internal class DeclaredClasses(
    private val keyed: Map<ClassSubject, BuiltinRecord<ClassSubject>>,
) : AbstractCollection<BuiltinRecord<ClassSubject>>() {
    override val size: Int get() = keyed.count { (key, record) -> key == record.subject }

    override fun isEmpty(): Boolean = !iterator().hasNext()

    override fun iterator(): Iterator<BuiltinRecord<ClassSubject>> =
        keyed.entries
            .asSequence()
            .filter { (key, record) -> key == record.subject }
            .map { it.value }
            .iterator()
}
