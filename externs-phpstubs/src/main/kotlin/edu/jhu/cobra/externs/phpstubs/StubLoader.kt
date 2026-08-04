package edu.jhu.cobra.externs.phpstubs

import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.Collections

/** Discovers and loads YAML stub files into a [StubRegistry]. */
object StubLoader {
    /** Loads all stub files under [resourceBase] and merges into a [StubRegistry]. */
    fun loadAll(resourceBase: String = "/stubs/"): StubRegistry {
        val base = if (resourceBase.endsWith("/")) resourceBase else "$resourceBase/"
        val results = discoverYamlFiles(base).map { yamlFile -> parseFile(base, yamlFile) }
        return buildRegistry(results)
    }

    private fun parseFile(
        base: String,
        yamlFile: String,
    ): YamlStubParser.ParseResult {
        val rawName = yamlFile.removeSuffix(".yaml").substringAfterLast('/')
        val extension = rawName.replace(Regex("_\\d+$"), "")
        return openResourceReader("$base$yamlFile").use { YamlStubParser.parse(it, extension) }
    }

    // associateBy keeps the last record per key, matching per-file overwrite order.
    private fun buildRegistry(results: List<YamlStubParser.ParseResult>): StubRegistry =
        StubRegistry(
            functions = unmodifiable(results.flatMap { it.functions }.associateBy { it.name.normalizeKey() }),
            classes = unmodifiable(results.flatMap { it.classes }.associateBy { it.name.normalizeKey() }),
            methods = unmodifiable(results.flatMap { it.methods }.associateBy { qualifiedKey(it.owningClass, it.name.normalizeKey()) }),
            constants = unmodifiable(results.flatMap { it.constants }.associateBy { it.name }),
            classConstants = unmodifiable(results.flatMap { it.classConstants }.associateBy { qualifiedKey(it.owningClass, it.name) }),
            properties =
                unmodifiable(
                    results.flatMap { it.properties }.associateBy { qualifiedKey(it.owningClass, it.name.normalizeKey()) },
                ),
        )

    private fun qualifiedKey(
        owningClass: String,
        memberKey: String,
    ): String = "${owningClass.normalizeKey()}::$memberKey"

    private fun <V> unmodifiable(map: Map<String, V>): Map<String, V> = Collections.unmodifiableMap(map)

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

    private fun String.normalizeKey(): String {
        val stripped = if (startsWith('/') || startsWith('\\')) substring(1) else this
        return stripped.lowercase()
    }

    private fun openResourceReader(path: String): BufferedReader {
        val stream =
            StubLoader::class.java.getResourceAsStream(path)
                ?: throw StubIndexNotFoundException(path)
        return BufferedReader(InputStreamReader(stream, Charsets.UTF_8))
    }
}
