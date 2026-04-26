package edu.jhu.cobra.externs.phpstubs

import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.Collections

/** Discovers and loads YAML stub files into a [StubRegistry]. */
object StubLoader {

    /** Loads all stub files under [resourceBase] and merges into a [StubRegistry]. */
    fun loadAll(resourceBase: String = "/stubs/"): StubRegistry {
        val base = if (resourceBase.endsWith("/")) resourceBase else "$resourceBase/"

        val functions = mutableMapOf<String, StubRecord.Function>()
        val classes = mutableMapOf<String, StubRecord.PhpClass>()
        val methods = mutableMapOf<String, StubRecord.Method>()
        val constants = mutableMapOf<String, StubRecord.Constant>()
        val classConstants = mutableMapOf<String, StubRecord.ClassConstant>()
        val properties = mutableMapOf<String, StubRecord.Property>()

        val yamlFiles = discoverYamlFiles(base)
        for (yamlFile in yamlFiles) {
            val rawName = yamlFile.removeSuffix(".yaml").substringAfterLast('/')
            val extension = rawName.replace(Regex("_\\d+$"), "")
            val reader = openResourceReader("$base$yamlFile")
            val result = reader.use { YamlStubParser.parse(it, extension) }

            for (record in result.functions) functions[record.name.normalizeKey()] = record
            for (record in result.classes) classes[record.name.normalizeKey()] = record
            for (record in result.methods) {
                methods["${record.owningClass.normalizeKey()}::${record.name.normalizeKey()}"] = record
            }
            for (record in result.constants) constants[record.name] = record
            for (record in result.classConstants) {
                classConstants["${record.owningClass.normalizeKey()}::${record.name}"] = record
            }
            for (record in result.properties) {
                properties["${record.owningClass.normalizeKey()}::${record.name.normalizeKey()}"] = record
            }
        }

        return StubRegistry(
            functions = Collections.unmodifiableMap(functions),
            classes = Collections.unmodifiableMap(classes),
            methods = Collections.unmodifiableMap(methods),
            constants = Collections.unmodifiableMap(constants),
            classConstants = Collections.unmodifiableMap(classConstants),
            properties = Collections.unmodifiableMap(properties),
        )
    }

    private fun discoverYamlFiles(base: String): List<String> {
        val indexPath = "${base}index.txt"
        val stream = StubLoader::class.java.getResourceAsStream(indexPath)
            ?: throw StubIndexNotFoundException(indexPath)
        return BufferedReader(InputStreamReader(stream, Charsets.UTF_8)).use { reader ->
            reader.lineSequence()
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
        val stream = StubLoader::class.java.getResourceAsStream(path)
            ?: throw StubIndexNotFoundException(path)
        return BufferedReader(InputStreamReader(stream, Charsets.UTF_8))
    }
}
