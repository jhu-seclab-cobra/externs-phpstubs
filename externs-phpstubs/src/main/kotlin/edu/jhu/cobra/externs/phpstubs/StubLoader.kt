package edu.jhu.cobra.externs.phpstubs

import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.Collections

/** Discovers and loads YAML stub files into a [StubRegistry]. */
public object StubLoader {
    // Strips the numeric split suffix (standard_1.yaml -> standard) when deriving the extension name.
    private val SPLIT_SUFFIX = Regex("_\\d+$")

    /**
     * Loads all stub files under [resourceBase] and merges into a [StubRegistry].
     *
     * @param resourceBase Classpath directory containing `index.txt` and the YAML stub files it lists.
     * @return Registry with one record per key across all listed files.
     * @throws StubIndexNotFoundException If the index or a listed stub file is missing.
     * @throws StubIndexInvalidException If a stub file is malformed or two files define the same normalized key.
     */
    public fun loadAll(resourceBase: String = "/stubs/"): StubRegistry {
        val base = if (resourceBase.endsWith("/")) resourceBase else "$resourceBase/"
        val results = discoverYamlFiles(base).map { yamlFile -> parseFile(base, yamlFile) }
        return buildRegistry(results)
    }

    /** One parsed YAML stub file together with its resource path for error reporting. */
    private data class ParsedFile(
        val path: String,
        val result: YamlStubParser.ParseResult,
    )

    private fun parseFile(
        base: String,
        yamlFile: String,
    ): ParsedFile {
        val rawName = yamlFile.removeSuffix(".yaml").substringAfterLast('/')
        val extension = rawName.replace(SPLIT_SUFFIX, "")
        val path = "$base$yamlFile"
        return ParsedFile(path, openResourceReader(path).use { YamlStubParser.parse(it, path, extension) })
    }

    private fun buildRegistry(files: List<ParsedFile>): StubRegistry =
        StubRegistry(
            functions = merge(files, { it.functions }) { it.name.normalizeStubKey() },
            classes = merge(files, { it.classes }) { it.name.normalizeStubKey() },
            methods = merge(files, { it.methods }) { qualifiedStubKey(it.owningClass, it.name.normalizeStubKey()) },
            constants = merge(files, { it.constants }) { it.name.stripLeadingSlash() },
            classConstants = merge(files, { it.classConstants }) { qualifiedStubKey(it.owningClass, it.name.stripLeadingSlash()) },
            properties = merge(files, { it.properties }) { qualifiedStubKey(it.owningClass, it.name.normalizeStubKey()) },
        )

    // Duplicate keys are corpus defects: fail loading instead of silently overwriting a record.
    private fun <R> merge(
        files: List<ParsedFile>,
        records: (YamlStubParser.ParseResult) -> List<R>,
        keyOf: (R) -> String,
    ): Map<String, R> {
        val merged = LinkedHashMap<String, R>()
        val origins = HashMap<String, String>()
        for ((path, result) in files) {
            for (record in records(result)) {
                val key = keyOf(record)
                val previous = origins.put(key, path)
                if (previous != null) {
                    throw StubIndexInvalidException("Duplicate stub key '$key' defined in $previous and $path")
                }
                merged[key] = record
            }
        }
        return Collections.unmodifiableMap(merged)
    }

    private fun discoverYamlFiles(base: String): List<String> {
        val indexPath = "${base}index.txt"
        val stream =
            StubLoader::class.java.getResourceAsStream(indexPath)
                ?: throw StubIndexNotFoundException(indexPath)
        return BufferedReader(InputStreamReader(stream, Charsets.UTF_8)).use { reader ->
            reader
                .lineSequence()
                .map { it.trim() }
                .filter { it.isNotBlank() && !it.startsWith("#") && it.endsWith(".yaml") }
                .toList()
        }
    }

    private fun openResourceReader(path: String): BufferedReader {
        val stream =
            StubLoader::class.java.getResourceAsStream(path)
                ?: throw StubIndexNotFoundException(path)
        return BufferedReader(InputStreamReader(stream, Charsets.UTF_8))
    }
}
