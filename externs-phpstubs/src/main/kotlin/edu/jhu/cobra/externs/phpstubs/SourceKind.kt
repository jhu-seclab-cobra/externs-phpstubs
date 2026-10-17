package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.SourceKindId

/**
 * The source kinds of the canonical vocabulary, one constant per name `vocabulary/vocabulary.yaml` declares.
 *
 * @property id The interned identifier the vocabulary document declares.
 */
public enum class SourceKind(
    public val id: SourceKindId,
) {
    USER_INPUT(SourceKindId("user-input")),
    EXTERNAL_INPUT(SourceKindId("external-input")),
}
