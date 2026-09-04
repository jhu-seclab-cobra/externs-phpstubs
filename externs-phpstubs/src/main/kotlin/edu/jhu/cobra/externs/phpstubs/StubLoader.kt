package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.DocumentSet
import edu.jhu.cobra.commons.phpmodels.DocumentSetException
import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelEntry
import edu.jhu.cobra.commons.phpmodels.ModelGenerator
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.PropertySubject
import edu.jhu.cobra.commons.phpmodels.ResourceOpener
import edu.jhu.cobra.commons.phpmodels.SubjectModel
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import java.io.InputStream
import java.util.Collections

/** Loads the declaration set through the library's set loader and builds a [StubRegistry] from it. */
public object StubLoader {
    // Strips the numeric split suffix (standard_1.yaml -> standard) when deriving the extension name.
    private val SPLIT_SUFFIX = Regex("_\\d+$")

    /**
     * Loads every document listed by `index.txt` under [resourceBase] and merges the entries into a registry.
     *
     * @param resourceBase Classpath directory holding `index.txt` and the documents it lists.
     * @return Registry with one entry per subject across all listed documents.
     * @throws StubIndexNotFoundException If the manifest or a listed document is missing.
     * @throws StubIndexInvalidException If the set fails loading otherwise or an entry violates a corpus rule.
     */
    public fun loadAll(resourceBase: String = StubResources.MODELS): StubRegistry {
        val base = StubResources.normalize(resourceBase)
        val builder = RegistryBuilder()
        for (document in loadSet(base).documents) {
            val path = base + document.path
            val extension =
                document.path
                    .removeSuffix(".yaml")
                    .substringAfterLast('/')
                    .replace(SPLIT_SUFFIX, "")
            for (entry in document.entries) builder.add(path, extension, entry)
        }
        return builder.freeze()
    }

    private fun loadSet(base: String): DocumentSet {
        val opener = RecordingOpener(StubResources.opener(base))
        return try {
            DocumentSetLoader.load(opener)
        } catch (failure: IllegalArgumentException) {
            throw stubFailure(base, opener.absent, failure)
        }
    }

    // A set failure naming a path the opener could not resolve is an absence; every other failure is invalidity.
    private fun stubFailure(
        base: String,
        absent: Set<String>,
        failure: IllegalArgumentException,
    ): RuntimeException {
        val path = (failure as? DocumentSetException)?.path
        return when {
            path != null && path in absent -> StubIndexNotFoundException(base + path)
            path != null -> StubIndexInvalidException("$base$path: ${failure.message}", failure)
            else -> StubIndexInvalidException("$base: ${failure.message}", failure)
        }
    }

    /** Remembers which paths resolved to nothing, so an absence failure can be told from a malformed one. */
    private class RecordingOpener(
        private val delegate: ResourceOpener,
    ) : ResourceOpener {
        val absent = HashSet<String>()

        override fun open(path: String): InputStream? = delegate.open(path).also { if (it == null) absent += path }
    }

    /** Accumulates entries per subject kind and enforces the corpus rules before freezing. */
    private class RegistryBuilder {
        private val functions = LinkedHashMap<FunctionSubject, StubEntry<FunctionSubject>>()
        private val classes = LinkedHashMap<ClassSubject, StubEntry<ClassSubject>>()
        private val methods = LinkedHashMap<MethodSubject, StubEntry<MethodSubject>>()
        private val constants = LinkedHashMap<ConstantSubject, StubEntry<ConstantSubject>>()
        private val classConstants = LinkedHashMap<ClassConstantSubject, StubEntry<ClassConstantSubject>>()
        private val properties = LinkedHashMap<PropertySubject, StubEntry<PropertySubject>>()
        private val origins = HashMap<ModelSubject, String>()

        fun add(
            path: String,
            extension: String,
            entry: ModelEntry,
        ) {
            when (entry) {
                is SubjectModel -> addModel(path, extension, entry)
                is ModelGenerator ->
                    throw StubIndexInvalidException("$path: generator '${entry.name}' is not stub data")
            }
        }

        private fun addModel(
            path: String,
            extension: String,
            model: SubjectModel,
        ) {
            val subject = model.subject
            requireSignature(path, model)
            recordOrigin(path, subject)
            when (subject) {
                is FunctionSubject -> functions[subject] = StubEntry(subject, model, extension)
                is ClassSubject -> classes[subject] = StubEntry(subject, model, extension)
                is MethodSubject -> methods[subject] = StubEntry(subject, model, extension)
                is ConstantSubject -> constants[subject] = StubEntry(subject, model, extension)
                is ClassConstantSubject -> classConstants[subject] = StubEntry(subject, model, extension)
                is PropertySubject -> properties[subject] = StubEntry(subject, model, extension)
                is VariableSubject ->
                    throw StubIndexInvalidException("$path: variable '$subject' is not stub data")
            }
        }

        private fun requireSignature(
            path: String,
            model: SubjectModel,
        ) {
            if (model.signature == null) {
                throw StubIndexInvalidException("$path: '${model.subject}' declares no signature")
            }
        }

        private fun recordOrigin(
            path: String,
            subject: ModelSubject,
        ) {
            val previous = origins.put(subject, path) ?: return
            throw StubIndexInvalidException("Duplicate subject '$subject' declared in $previous and $path")
        }

        fun freeze(): StubRegistry =
            StubRegistry(
                functions = Collections.unmodifiableMap(functions),
                classes = Collections.unmodifiableMap(classes),
                methods = Collections.unmodifiableMap(methods),
                constants = Collections.unmodifiableMap(constants),
                classConstants = Collections.unmodifiableMap(classConstants),
                properties = Collections.unmodifiableMap(properties),
            )
    }
}
