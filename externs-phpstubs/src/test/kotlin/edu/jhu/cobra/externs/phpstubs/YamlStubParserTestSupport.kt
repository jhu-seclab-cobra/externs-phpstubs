package edu.jhu.cobra.externs.phpstubs

import java.io.BufferedReader
import java.io.StringReader

/**
 * Shared fixtures for the [YamlStubParser] test split.
 *
 * - [STUB_YAML_SOURCE] — source name expected in every parse error message.
 * - [parseStubYaml] — parses an inline YAML snippet as one stub file.
 */

internal const val STUB_YAML_SOURCE = "test.yaml"

internal fun parseStubYaml(
    yaml: String,
    extension: String = "standard",
): YamlStubParser.ParseResult = YamlStubParser.parse(BufferedReader(StringReader(yaml)), STUB_YAML_SOURCE, extension)
