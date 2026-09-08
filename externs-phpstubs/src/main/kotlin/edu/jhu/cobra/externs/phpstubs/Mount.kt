package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.CategoryMapping
import edu.jhu.cobra.commons.phpmodels.Document
import edu.jhu.cobra.commons.phpmodels.DocumentSet
import edu.jhu.cobra.commons.phpmodels.DocumentSetException
import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.ModelEntry
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.PolicyRow
import edu.jhu.cobra.commons.phpmodels.ResourceOpener
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import edu.jhu.cobra.commons.phpmodels.Verification
import edu.jhu.cobra.commons.phpmodels.Vocabulary
import java.io.InputStream

/**
 * One document set as mounted: its position in merge order, its verification kind, the vocabulary and
 * policy rows it declares, and its entries, each paired with the PHP extension its document path yields
 * for the generated set and null for every other set.
 */
internal data class Mount(
    val position: Int,
    val verification: Verification,
    val vocabulary: Vocabulary,
    val policy: List<PolicyRow>,
    val entries: List<Pair<ModelEntry, String?>>,
)

/**
 * Builds mounts in order, decoding each set against the vocabulary the earlier mounts accumulated.
 * A set-load failure naming a path the opener could not resolve is [StubIndexNotFoundException];
 * every other failure is [StubIndexInvalidException] with the format library's cause attached.
 */
internal class MountSequence(
    initial: List<Mount> = emptyList(),
) {
    private val mounts = initial.toMutableList()
    private var vocabulary = initial.fold(Vocabulary.EMPTY) { acc, mount -> acc.merge(mount.vocabulary) }

    /** The mounts built so far, in position order. */
    fun toList(): List<Mount> = mounts.toList()

    /**
     * Decodes and appends one set.
     *
     * @param label The root the failure messages name.
     * @param open The opener over the set's root.
     * @param mapping The category mapping the set decodes under, or null for a set in canonical names.
     * @param fallback The verification of a set without `provenance.yaml`, or null when one is required.
     * @param corpus True for the generated declaration set: the corpus rules apply and extensions derive.
     */
    fun mount(
        label: String,
        open: ResourceOpener,
        mapping: CategoryMapping? = null,
        fallback: Verification? = Verification.MANUAL,
        corpus: Boolean = false,
    ): MountSequence {
        val set = loadSet(label, open, mapping)
        val verification =
            set.provenance?.verification ?: fallback
                ?: throw StubIndexInvalidException("$label: bundled set declares no provenance")
        val entries = if (corpus) corpusEntries(label, set.documents) else set.entries.map { it to null }
        mounts += Mount(mounts.size, verification, set.vocabulary, set.policy, entries)
        vocabulary = vocabulary.merge(set.vocabulary)
        return this
    }

    private fun loadSet(
        label: String,
        open: ResourceOpener,
        mapping: CategoryMapping?,
    ): DocumentSet {
        val opener = RecordingOpener(open)
        return try {
            DocumentSetLoader.load(opener, vocabulary, mapping)
        } catch (failure: IllegalArgumentException) {
            throw stubFailure(label, opener.absent, failure)
        }
    }

    // A set failure naming a path the opener could not resolve is an absence; every other failure is invalidity.
    private fun stubFailure(
        label: String,
        absent: Set<String>,
        failure: IllegalArgumentException,
    ): RuntimeException {
        val path = (failure as? DocumentSetException)?.path
        return when {
            path != null && path in absent -> StubIndexNotFoundException(label + path)
            path != null -> StubIndexInvalidException("$label$path: ${failure.message}", failure)
            else -> StubIndexInvalidException("$label: ${failure.message}", failure)
        }
    }

    // The corpus rules of the generated set: no variable, every entry signed and unconditional, one document per subject.
    private fun corpusEntries(
        label: String,
        documents: List<Document>,
    ): List<Pair<ModelEntry, String?>> {
        val origins = HashMap<ModelSubject, String>()
        val entries = ArrayList<Pair<ModelEntry, String?>>()
        for (document in documents) {
            val path = label + document.path
            val extension = extensionOf(document.path)
            for (entry in document.entries) {
                requireCorpusEntry(path, entry)
                origins.put(entry.subject, path)?.let { previous ->
                    throw StubIndexInvalidException("Duplicate subject '${entry.subject}' declared in $previous and $path")
                }
                entries += entry to extension
            }
        }
        return entries
    }

    private fun requireCorpusEntry(
        path: String,
        entry: ModelEntry,
    ) {
        val reason =
            when {
                entry.subject is VariableSubject -> "variable '${entry.subject}' is not stub data"
                entry.signature == null -> "'${entry.subject}' declares no signature"
                entry.condition != null -> "'${entry.subject}' declares a condition"
                else -> return
            }
        throw StubIndexInvalidException("$path: $reason")
    }

    /** Remembers which paths resolved to nothing, so an absence failure can be told from a malformed one. */
    private class RecordingOpener(
        private val delegate: ResourceOpener,
    ) : ResourceOpener {
        val absent = HashSet<String>()

        override fun open(path: String): InputStream? = delegate.open(path).also { if (it == null) absent += path }
    }

    companion object {
        private const val DOCUMENT_SUFFIX = ".yaml"

        // Strips the numeric split suffix (standard_1.yaml -> standard) when deriving the extension name.
        private val SPLIT_SUFFIX = Regex("_\\d+$")

        /** The PHP extension a generated document's path yields: file name without suffix and split index. */
        fun extensionOf(path: String): String =
            path
                .removeSuffix(DOCUMENT_SUFFIX)
                .substringAfterLast('/')
                .replace(SPLIT_SUFFIX, "")
    }
}
