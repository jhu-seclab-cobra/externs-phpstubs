package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ResourceOpener

/** The classpath roots of the document sets this module ships, and the opener that reads them. */
public object StubResources {
    /** Root of the generated declaration set: one signature-bearing model per built-in. */
    public const val MODELS: String = "/models/"

    /** Root of the taint set: sinks, sanitizers, and sources in psalm's names. */
    public const val TAINT: String = "/taint/"

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
