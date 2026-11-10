package edu.jhu.cobra.externs.phpstubs

import org.yaml.snakeyaml.LoaderOptions
import org.yaml.snakeyaml.Yaml
import org.yaml.snakeyaml.constructor.SafeConstructor
import org.yaml.snakeyaml.error.YAMLException
import org.yaml.snakeyaml.nodes.MappingNode
import org.yaml.snakeyaml.nodes.Node
import org.yaml.snakeyaml.nodes.ScalarNode
import org.yaml.snakeyaml.nodes.SequenceNode
import org.yaml.snakeyaml.nodes.Tag

/**
 * One selectable generated Document Set for a Composer package.
 *
 * @property `package` Exact Composer package name.
 * @property version Library version or constraint described by the stubs; unknown when unspecified.
 * @property upstreams Upstream names with releases and source identities.
 * @property root Classpath directory containing the set manifest and notices.
 */
public data class LibrarySet(
    public val `package`: String,
    public val version: String,
    public val upstreams: List<String>,
    public val root: String,
)

private const val CATALOG = "/taint-libraries/catalog.yaml"

/** Decodes the generated catalog; malformed shipped metadata is a packaging error. */
internal fun libraryCatalog(): List<LibrarySet> {
    val options = LoaderOptions().apply { isAllowDuplicateKeys = false }
    val yaml = Yaml(SafeConstructor(options))
    val stream = StubResources::class.java.getResourceAsStream(CATALOG) ?: throw StubIndexNotFoundException(CATALOG)
    val node =
        try {
            stream.bufferedReader(Charsets.UTF_8).use(yaml::compose)
        } catch (failure: YAMLException) {
            throw StubIndexInvalidException("$CATALOG: ${failure.message}", failure)
        }
    val rows = (node as? SequenceNode)?.value ?: invalidCatalog()
    val libraries = rows.map(::libraryRow)
    if (libraries.map { it.`package` }.distinct().size != libraries.size) invalidCatalog()
    return libraries
}

private fun libraryRow(node: Node): LibrarySet {
    val pairs = (node as? MappingNode)?.value ?: invalidCatalog()
    val fields = pairs.associate { catalogString(it.keyNode) to it.valueNode }
    if (fields.keys != setOf("package", "version", "upstreams", "root") || fields.size != pairs.size) invalidCatalog()
    val upstreams = (fields.getValue("upstreams") as? SequenceNode)?.value ?: invalidCatalog()
    val name = catalogString(fields.getValue("package"))
    val root = catalogString(fields.getValue("root"))
    if (!Regex("[a-z0-9_.-]+/[a-z0-9_.-]+").matches(name)) invalidCatalog()
    if (root != "/taint-libraries/${name.replace('/', '-')}/" || upstreams.isEmpty()) invalidCatalog()
    return LibrarySet(name, catalogString(fields.getValue("version")), upstreams.map(::catalogString), root)
}

private fun catalogString(node: Node): String {
    val scalar = node as? ScalarNode ?: invalidCatalog()
    if (scalar.tag != Tag.STR || scalar.value.isEmpty()) invalidCatalog()
    return scalar.value
}

private fun invalidCatalog(): Nothing = throw StubIndexInvalidException("$CATALOG: invalid library catalog")
