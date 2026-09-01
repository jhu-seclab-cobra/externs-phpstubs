package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelEntry
import edu.jhu.cobra.commons.phpmodels.ModelGenerator
import edu.jhu.cobra.commons.phpmodels.ModelLoader
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.PropertySubject
import edu.jhu.cobra.commons.phpmodels.SubjectModel
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import java.io.InputStream
import java.util.Collections

/** Discovers the manifest-listed model documents and builds a [StubRegistry] from them. */
public object StubLoader {
    // Strips the numeric split suffix (standard_1.yaml -> standard) when deriving the extension name.
    private val SPLIT_SUFFIX = Regex("_\\d+$")

    /**
     * Loads every document listed by `index.txt` under [resourceBase] and merges the entries into a registry.
     *
     * @param resourceBase Classpath directory holding `index.txt` and the documents it lists.
     * @return Registry with one entry per subject across all listed documents.
     * @throws StubIndexNotFoundException If the manifest or a listed document is missing.
     * @throws StubIndexInvalidException If a document fails decoding or violates a corpus rule.
     */
    public fun loadAll(resourceBase: String = "/models/"): StubRegistry {
        val base = if (resourceBase.endsWith("/")) resourceBase else "$resourceBase/"
        val builder = RegistryBuilder()
        for (relative in discoverDocuments(base)) {
            val document = decodeDocument(base, relative)
            for (entry in document.entries) builder.add(document, entry)
        }
        return builder.freeze()
    }

    /** One decoded document with its resource path and derived extension. */
    private class Document(
        val path: String,
        val extension: String,
        val entries: List<ModelEntry>,
    )

    private fun decodeDocument(
        base: String,
        relative: String,
    ): Document {
        val path = "$base$relative"
        val extension = relative.removeSuffix(".yaml").substringAfterLast('/').replace(SPLIT_SUFFIX, "")
        val entries =
            try {
                ModelLoader.load(openResource(path))
            } catch (failure: IllegalArgumentException) {
                throw StubIndexInvalidException("$path: ${failure.message}", failure)
            }
        return Document(path, extension, entries)
    }

    private fun discoverDocuments(base: String): List<String> {
        val indexPath = "${base}index.txt"
        return openResource(indexPath).bufferedReader(Charsets.UTF_8).use { reader ->
            reader
                .lineSequence()
                .map { it.trim() }
                .filter { it.isNotBlank() && !it.startsWith("#") }
                .toList()
        }
    }

    private fun openResource(path: String): InputStream =
        StubLoader::class.java.getResourceAsStream(path) ?: throw StubIndexNotFoundException(path)

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
            document: Document,
            entry: ModelEntry,
        ) {
            when (entry) {
                is SubjectModel -> addModel(document, entry)
                is ModelGenerator ->
                    throw StubIndexInvalidException("${document.path}: generator '${entry.name}' is not stub data")
            }
        }

        private fun addModel(
            document: Document,
            model: SubjectModel,
        ) {
            val subject = model.subject
            requireSignature(document, model)
            recordOrigin(document, subject)
            when (subject) {
                is FunctionSubject -> functions[subject] = StubEntry(subject, model, document.extension)
                is ClassSubject -> classes[subject] = StubEntry(subject, model, document.extension)
                is MethodSubject -> methods[subject] = StubEntry(subject, model, document.extension)
                is ConstantSubject -> constants[subject] = StubEntry(subject, model, document.extension)
                is ClassConstantSubject -> classConstants[subject] = StubEntry(subject, model, document.extension)
                is PropertySubject -> properties[subject] = StubEntry(subject, model, document.extension)
                is VariableSubject ->
                    throw StubIndexInvalidException("${document.path}: variable '$subject' is not stub data")
            }
        }

        private fun requireSignature(
            document: Document,
            model: SubjectModel,
        ) {
            if (model.signature == null) {
                throw StubIndexInvalidException("${document.path}: '${model.subject}' declares no signature")
            }
        }

        private fun recordOrigin(
            document: Document,
            subject: ModelSubject,
        ) {
            val previous = origins.put(subject, document.path) ?: return
            throw StubIndexInvalidException("Duplicate subject '$subject' declared in $previous and ${document.path}")
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
