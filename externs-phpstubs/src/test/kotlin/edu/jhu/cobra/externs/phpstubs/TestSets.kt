package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.CategoryMapping
import edu.jhu.cobra.commons.phpmodels.DocumentSet
import edu.jhu.cobra.commons.phpmodels.DocumentSetLoader
import edu.jhu.cobra.commons.phpmodels.ResourceOpener
import edu.jhu.cobra.commons.phpmodels.Verification
import edu.jhu.cobra.commons.phpmodels.Vocabulary

/** In-memory document sets for the merge and mount tests: one YAML document plus an optional vocabulary. */
internal object TestSets {
    const val VOCABULARY = """
vulnClasses:
  - {name: sqli, description: SQL injection}
  - {name: xss, description: Cross-site scripting}
provenances:
  - {name: user-input, description: Request data}
"""

    fun opener(vararg files: Pair<String, String>): ResourceOpener {
        val byPath = files.toMap()
        return ResourceOpener { path -> byPath[path]?.byteInputStream() }
    }

    fun set(
        document: String,
        vocabulary: String? = VOCABULARY,
        context: Vocabulary = Vocabulary.EMPTY,
        mapping: CategoryMapping? = null,
    ): DocumentSet {
        val files = listOfNotNull("index.txt" to "models.yaml\n", "models.yaml" to document, vocabulary?.let { "vocabulary.yaml" to it })
        return DocumentSetLoader.load(opener(*files.toTypedArray()), context, mapping)
    }

    fun mount(
        position: Int,
        verification: Verification,
        document: String,
        vocabulary: String? = VOCABULARY,
        context: Vocabulary = Vocabulary.EMPTY,
        extension: String? = null,
    ): Mount {
        val set = set(document, vocabulary, context)
        return Mount(position, verification, set.vocabulary, set.policy, set.entries.map { it to extension })
    }
}
