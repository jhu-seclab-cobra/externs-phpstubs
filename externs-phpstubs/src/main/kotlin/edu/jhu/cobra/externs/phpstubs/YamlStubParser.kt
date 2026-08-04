package edu.jhu.cobra.externs.phpstubs

import org.yaml.snakeyaml.Yaml
import java.io.BufferedReader

/** Parses unified YAML stub files into [StubRecord] instances. */
public object YamlStubParser {
    /**
     * Categorized parse output from a single YAML stub file.
     */
    public data class ParseResult(
        val functions: List<StubRecord.Function> = emptyList(),
        val classes: List<StubRecord.PhpClass> = emptyList(),
        val methods: List<StubRecord.Method> = emptyList(),
        val constants: List<StubRecord.Constant> = emptyList(),
        val classConstants: List<StubRecord.ClassConstant> = emptyList(),
        val properties: List<StubRecord.Property> = emptyList(),
    )

    /**
     * Parses a unified YAML stub file and returns categorized [StubRecord] lists.
     *
     * @param reader Source of YAML content.
     * @param source Resource path or name of the YAML file; prefixed to every error message.
     * @param extension The PHP extension name to assign to each record.
     * @return Categorized [ParseResult] with records for each entity type.
     * @throws StubIndexInvalidException If a tag is unknown or required fields are missing; the message names [source].
     */
    public fun parse(
        reader: BufferedReader,
        source: String,
        extension: String,
    ): ParseResult {
        val raw = Yaml().load<Any>(reader) ?: return ParseResult()
        val entries =
            raw as? List<*>
                ?: throw StubIndexInvalidException("$source: Expected YAML list at top level")
        val entryParser = StubEntryParser(source, extension)
        val records = entries.map { entry -> entryParser.parseEntry(entry) }
        return ParseResult(
            functions = records.filterIsInstance<StubRecord.Function>(),
            classes = records.filterIsInstance<StubRecord.PhpClass>(),
            methods = records.filterIsInstance<StubRecord.Method>(),
            constants = records.filterIsInstance<StubRecord.Constant>(),
            classConstants = records.filterIsInstance<StubRecord.ClassConstant>(),
            properties = records.filterIsInstance<StubRecord.Property>(),
        )
    }

    /**
     * Maps a YAML visibility string to [Visibility].
     * Null means the field is absent and defaults to [Visibility.PUBLIC].
     *
     * @param raw The YAML visibility string, or null when the field is absent.
     * @param source Resource path or name of the YAML file; prefixed to the error message.
     * @throws StubIndexInvalidException If [raw] is not a recognized visibility.
     */
    internal fun mapVisibility(
        raw: String?,
        source: String,
    ): Visibility =
        when (raw?.lowercase()) {
            null -> Visibility.PUBLIC
            "public" -> Visibility.PUBLIC
            "protected" -> Visibility.PROTECTED
            "private" -> Visibility.PRIVATE
            else -> throw StubIndexInvalidException("$source: Unknown visibility: $raw")
        }

    /**
     * Maps a YAML type string to [PhpType]. Union types collapse to [PhpType.MIXED].
     *
     * @param typeStr The YAML type string.
     * @param source Resource path or name of the YAML file; prefixed to the error message.
     * @throws StubIndexInvalidException If [typeStr] is not a recognized type.
     */
    internal fun mapPhpType(
        typeStr: String,
        source: String,
    ): PhpType {
        if ("|" in typeStr) return PhpType.MIXED
        return when (typeStr.lowercase()) {
            "string" -> PhpType.STRING
            "int", "integer" -> PhpType.INT
            "float", "double" -> PhpType.FLOAT
            "bool", "boolean" -> PhpType.BOOL
            "array" -> PhpType.ARRAY
            "object" -> PhpType.OBJECT
            "mixed" -> PhpType.MIXED
            "void" -> PhpType.VOID
            "null" -> PhpType.NULL
            "callable" -> PhpType.CALLABLE
            "resource" -> PhpType.RESOURCE
            else -> throw StubIndexInvalidException("$source: Unknown PHP type: $typeStr")
        }
    }
}

/** Parses the entries of one YAML stub file; every error message is prefixed with the source path. */
private class StubEntryParser(
    private val source: String,
    private val extension: String,
) {
    fun parseEntry(entry: Any?): StubRecord {
        val map = entry as? Map<*, *> ?: invalid("Expected map entry in YAML list")
        val tag = map["tag"] as? String ?: invalid("Missing 'tag' field in entry")
        return when (tag) {
            "function" -> parseFunction(map)
            "method" -> parseMethod(map)
            "class" -> parseClass(map)
            "constant" -> parseConstant(map)
            "class_constant" -> parseClassConstant(map)
            "property" -> parseProperty(map)
            else -> invalid("Unknown tag: $tag")
        }
    }

    private fun invalid(reason: String): Nothing = throw StubIndexInvalidException("$source: $reason")

    private fun mapType(typeStr: String): PhpType = YamlStubParser.mapPhpType(typeStr, source)

    private fun mapVisibility(raw: String?): Visibility = YamlStubParser.mapVisibility(raw, source)

    private fun parseFunction(map: Map<*, *>): StubRecord.Function =
        StubRecord.Function(
            name = requireString(map, "name"),
            extension = extension,
            params = parseParams(map["params"]),
            returnType = mapType(map["return"]?.toString() ?: "mixed"),
            flowsToReturn = parseFlowsToReturn(map["flowsToReturn"]),
        )

    private fun parseMethod(map: Map<*, *>): StubRecord.Method =
        StubRecord.Method(
            name = requireString(map, "name"),
            extension = extension,
            owningClass = requireString(map, "class"),
            params = parseParams(map["params"]),
            returnType = mapType(map["return"]?.toString() ?: "mixed"),
            flowsToReturn = parseFlowsToReturn(map["flowsToReturn"]),
            isStatic = map["static"] as? Boolean ?: false,
            visibility = mapVisibility(map["visibility"]?.toString()),
        )

    private fun parseClass(map: Map<*, *>): StubRecord.PhpClass =
        StubRecord.PhpClass(
            name = requireString(map, "name"),
            extension = extension,
            parent = map["parent"]?.toString(),
            interfaces = parseStringList(map["interfaces"]),
            isAbstract = map["abstract"] as? Boolean ?: false,
            isFinal = map["final"] as? Boolean ?: false,
        )

    private fun parseConstant(map: Map<*, *>): StubRecord.Constant {
        val name = requireString(map, "name")
        return StubRecord.Constant(
            name = name,
            extension = extension,
            type = mapType(map["type"]?.toString() ?: invalid("Missing 'type' for constant '$name'")),
            value = (map["value"] ?: invalid("Missing 'value' for constant '$name'")).toString(),
        )
    }

    private fun parseClassConstant(map: Map<*, *>): StubRecord.ClassConstant {
        val name = requireString(map, "name")
        val className = requireString(map, "class")
        return StubRecord.ClassConstant(
            name = name,
            extension = extension,
            owningClass = className,
            type =
                mapType(
                    map["type"]?.toString()
                        ?: invalid("Missing 'type' for class_constant '$className::$name'"),
                ),
            value =
                (
                    map["value"]
                        ?: invalid("Missing 'value' for class_constant '$className::$name'")
                ).toString(),
            visibility = mapVisibility(map["visibility"]?.toString()),
        )
    }

    private fun parseProperty(map: Map<*, *>): StubRecord.Property =
        StubRecord.Property(
            name = requireString(map, "name"),
            extension = extension,
            owningClass = requireString(map, "class"),
            type = mapType(map["type"]?.toString() ?: "mixed"),
            isStatic = map["static"] as? Boolean ?: false,
            visibility = mapVisibility(map["visibility"]?.toString()),
        )

    private fun requireString(
        map: Map<*, *>,
        key: String,
    ): String = map[key]?.toString() ?: invalid("Missing required field '$key'")

    private fun parseParams(raw: Any?): List<StubParam> {
        if (raw == null) return emptyList()
        val list = raw as? List<*> ?: invalid("Expected list for 'params'")
        return list.map { item -> parseParam(item) }
    }

    private fun parseParam(item: Any?): StubParam {
        val paramMap = item as? Map<*, *> ?: invalid("Expected map in 'params' list")
        val name = paramMap["name"]?.toString() ?: invalid("Missing 'name' in param entry")
        val default = paramMap["default"]?.toString()
        return StubParam(
            name = name,
            type = mapType(paramMap["type"]?.toString() ?: "mixed"),
            optional = paramMap["optional"] as? Boolean ?: (default != null),
            defaultValue = default,
        )
    }

    private fun parseFlowsToReturn(raw: Any?): Set<Int> {
        if (raw == null) return emptySet()
        val list = raw as? List<*> ?: invalid("Expected list for 'flowsToReturn'")
        return list
            .map { item ->
                (item as? Number)?.toInt() ?: invalid("Expected integer in 'flowsToReturn'")
            }.toSet()
    }

    private fun parseStringList(raw: Any?): List<String> {
        if (raw == null) return emptyList()
        val list = raw as? List<*> ?: invalid("Expected list for 'interfaces'")
        return list.map { it.toString() }
    }
}
