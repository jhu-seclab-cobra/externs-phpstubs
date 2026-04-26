package edu.jhu.cobra.externs.phpstubs

import org.yaml.snakeyaml.Yaml
import java.io.BufferedReader

/** Parses unified YAML stub files into [StubRecord] instances. */
object YamlStubParser {

    /**
     * Categorized parse output from a single YAML stub file.
     */
    data class ParseResult(
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
     * @param extension The PHP extension name to assign to each record.
     * @return Categorized [ParseResult] with records for each entity type.
     * @throws StubIndexInvalidException If a tag is unknown or required fields are missing.
     */
    fun parse(reader: BufferedReader, extension: String): ParseResult {
        val raw = Yaml().load<Any>(reader) ?: return ParseResult()
        val entries = raw as? List<*>
            ?: throw StubIndexInvalidException("Expected YAML list at top level")

        val functions = mutableListOf<StubRecord.Function>()
        val classes = mutableListOf<StubRecord.PhpClass>()
        val methods = mutableListOf<StubRecord.Method>()
        val constants = mutableListOf<StubRecord.Constant>()
        val classConstants = mutableListOf<StubRecord.ClassConstant>()
        val properties = mutableListOf<StubRecord.Property>()

        for (entry in entries) {
            val map = entry as? Map<*, *>
                ?: throw StubIndexInvalidException("Expected map entry in YAML list")
            val tag = map["tag"] as? String
                ?: throw StubIndexInvalidException("Missing 'tag' field in entry")

            when (tag) {
                "function" -> functions.add(parseFunction(map, extension))
                "method" -> methods.add(parseMethod(map, extension))
                "class" -> classes.add(parseClass(map, extension))
                "constant" -> constants.add(parseConstant(map, extension))
                "class_constant" -> classConstants.add(parseClassConstant(map, extension))
                "property" -> properties.add(parseProperty(map, extension))
                else -> throw StubIndexInvalidException("Unknown tag: $tag")
            }
        }

        return ParseResult(
            functions = functions,
            classes = classes,
            methods = methods,
            constants = constants,
            classConstants = classConstants,
            properties = properties,
        )
    }

    private fun parseFunction(map: Map<*, *>, extension: String): StubRecord.Function {
        val name = requireString(map, "name")
        return StubRecord.Function(
            name = name,
            extension = extension,
            params = parseParams(map["params"]),
            returnType = mapPhpType(map["return"]?.toString() ?: "mixed"),
            flowsToReturn = parseFlowsToReturn(map["flowsToReturn"]),
        )
    }

    private fun parseMethod(map: Map<*, *>, extension: String): StubRecord.Method {
        return StubRecord.Method(
            name = requireString(map, "name"),
            extension = extension,
            owningClass = requireString(map, "class"),
            params = parseParams(map["params"]),
            returnType = mapPhpType(map["return"]?.toString() ?: "mixed"),
            flowsToReturn = parseFlowsToReturn(map["flowsToReturn"]),
            isStatic = map["static"] as? Boolean ?: false,
            visibility = mapVisibility(map["visibility"]?.toString()),
        )
    }

    private fun parseClass(map: Map<*, *>, extension: String): StubRecord.PhpClass {
        return StubRecord.PhpClass(
            name = requireString(map, "name"),
            extension = extension,
            parent = map["parent"]?.toString(),
            interfaces = parseStringList(map["interfaces"]),
            isAbstract = map["abstract"] as? Boolean ?: false,
            isFinal = map["final"] as? Boolean ?: false,
        )
    }

    private fun parseConstant(map: Map<*, *>, extension: String): StubRecord.Constant {
        val name = requireString(map, "name")
        return StubRecord.Constant(
            name = name,
            extension = extension,
            type = mapPhpType(
                map["type"]?.toString()
                    ?: throw StubIndexInvalidException("Missing 'type' for constant '$name'"),
            ),
            value = (map["value"]
                ?: throw StubIndexInvalidException("Missing 'value' for constant '$name'"))
                .toString(),
        )
    }

    private fun parseClassConstant(map: Map<*, *>, extension: String): StubRecord.ClassConstant {
        val name = requireString(map, "name")
        val className = requireString(map, "class")
        return StubRecord.ClassConstant(
            name = name,
            extension = extension,
            owningClass = className,
            type = mapPhpType(
                map["type"]?.toString()
                    ?: throw StubIndexInvalidException("Missing 'type' for class_constant '$className::$name'"),
            ),
            value = (map["value"]
                ?: throw StubIndexInvalidException("Missing 'value' for class_constant '$className::$name'"))
                .toString(),
            visibility = mapVisibility(map["visibility"]?.toString()),
        )
    }

    private fun parseProperty(map: Map<*, *>, extension: String): StubRecord.Property {
        return StubRecord.Property(
            name = requireString(map, "name"),
            extension = extension,
            owningClass = requireString(map, "class"),
            type = mapPhpType(map["type"]?.toString() ?: "mixed"),
            isStatic = map["static"] as? Boolean ?: false,
            visibility = mapVisibility(map["visibility"]?.toString()),
        )
    }

    private fun requireString(map: Map<*, *>, key: String): String =
        map[key]?.toString()
            ?: throw StubIndexInvalidException("Missing required field '$key'")

    private fun parseParams(raw: Any?): List<StubParam> {
        if (raw == null) return emptyList()
        val list = raw as? List<*>
            ?: throw StubIndexInvalidException("Expected list for 'params'")
        return list.map { item ->
            val paramMap = item as? Map<*, *>
                ?: throw StubIndexInvalidException("Expected map in 'params' list")
            val name = paramMap["name"]?.toString()
                ?: throw StubIndexInvalidException("Missing 'name' in param entry")
            val type = mapPhpType(paramMap["type"]?.toString() ?: "mixed")
            val default = paramMap["default"]?.toString()
            val optional = paramMap["optional"] as? Boolean ?: (default != null)
            StubParam(
                name = name,
                type = type,
                optional = optional,
                defaultValue = default,
            )
        }
    }

    private fun parseFlowsToReturn(raw: Any?): Set<Int> {
        if (raw == null) return emptySet()
        val list = raw as? List<*>
            ?: throw StubIndexInvalidException("Expected list for 'flowsToReturn'")
        return list.map { item ->
            (item as? Number)?.toInt()
                ?: throw StubIndexInvalidException("Expected integer in 'flowsToReturn'")
        }.toSet()
    }

    private fun parseStringList(raw: Any?): List<String> {
        if (raw == null) return emptyList()
        val list = raw as? List<*>
            ?: throw StubIndexInvalidException("Expected list for 'interfaces'")
        return list.map { it.toString() }
    }

    /**
     * Maps a YAML visibility string to [Visibility].
     * Unrecognized or null values default to [Visibility.PUBLIC].
     */
    internal fun mapVisibility(raw: String?): Visibility =
        when (raw?.lowercase()) {
            "protected" -> Visibility.PROTECTED
            "private" -> Visibility.PRIVATE
            else -> Visibility.PUBLIC
        }

    internal fun mapPhpType(typeStr: String): PhpType {
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
            else -> PhpType.MIXED
        }
    }
}
