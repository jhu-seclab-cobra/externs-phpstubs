package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.OriginId

/**
 * The origin colors of the canonical vocabulary, one constant per name `vocabulary/vocabulary.yaml` declares.
 *
 * @property id The interned identifier the vocabulary document declares.
 */
public enum class Origin(
    public val id: OriginId,
) {
    USER_INPUT(OriginId("user-input")),
    EXTERNAL_INPUT(OriginId("external-input")),
}
