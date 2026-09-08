package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ResourceOpener

/** The classpath roots of the document sets this module ships, the psalm mapping, and the opener over a root. */
public object StubResources {
    /** Root of the generated declaration set: one signature-bearing model per built-in. */
    public const val MODELS: String = "/models/"

    /** Root of the taint set: sinks, sanitizers, and sources in psalm's names. */
    public const val TAINT: String = "/taint/"

    /**
     * Root of the hand-maintained taint rules set: taint assertions beyond psalm's, in psalm's names
     * plus its own additions. The name is distinct from any consumer directory on a shared classpath.
     */
    public const val TAINT_RULES: String = "/taint-rules/"

    /**
     * Root of the hand-maintained value rules set: value-semantics units the generated declarations
     * lack or state wrongly, reviewed against the PHP manual. Names no category or color.
     */
    public const val VALUE_RULES: String = "/value-rules/"

    /** Root of the canonical vocabulary set: the danger categories, origin colors, and policy every record speaks. */
    public const val VOCABULARY: String = "/vocabulary/"

    /** The psalm mapping: the translation of the taint set and the taint rules set into the canonical vocabulary. */
    public const val PSALM_MAPPING: String = "/vocabulary/psalm-mapping.yaml"

    /**
     * Resolves paths relative to [root] on this module's classpath.
     *
     * @param root Classpath directory of one document set; the trailing slash is optional.
     * @return An opener yielding the resource stream, or null for a path that resolves to nothing.
     */
    public fun opener(root: String): ResourceOpener {
        val base = normalize(root)
        return ResourceOpener { path -> StubResources::class.java.getResourceAsStream(base + path) }
    }

    /** Returns [root] with exactly one trailing slash. */
    internal fun normalize(root: String): String = if (root.endsWith("/")) root else "$root/"
}
