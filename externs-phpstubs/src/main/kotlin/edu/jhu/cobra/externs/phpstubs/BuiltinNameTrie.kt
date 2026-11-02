package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ModelSubject

/** Canonical signed records of one kind, built only while its effective merge is assembled. */
internal class BuiltinNameTrie<S : ModelSubject> {
    private class Node<S : ModelSubject> {
        val children = LinkedHashMap<Char, Node<S>>()
        var record: BuiltinRecord<S>? = null
    }

    private val root = Node<S>()
    var nodeCount: Int = 1
        private set
    var insertedCharacters: Int = 0
        private set

    fun add(record: BuiltinRecord<S>) {
        check(record.signature != null) { "Only declared records enter the canonical name trie" }
        var node = root
        for (character in record.subject.name) {
            insertedCharacters++
            node =
                node.children.getOrPut(character) {
                    nodeCount++
                    Node()
                }
        }
        check(node.record == null) { "A canonical subject is inserted once" }
        node.record = record
    }

    fun matches(pattern: NamePattern): Cursor = Cursor(pattern)

    /** One real query cursor; its ordinary counters describe visited trie nodes and emitted identities. */
    inner class Cursor(
        private val pattern: NamePattern,
    ) : Iterator<BuiltinRecord<S>> {
        private val frames = ArrayDeque<Frame<S>>()
        private var pending: BuiltinRecord<S>? = null
        var visitedNodes: Int = 0
            private set
        var emittedRecords: Int = 0
            private set
        var maxFrames: Int = 1
            private set

        init {
            frames.addLast(Frame(root.children.entries.iterator(), pattern.initial()))
        }

        override fun hasNext(): Boolean {
            if (pending == null) pending = findNext()
            return pending != null
        }

        override fun next(): BuiltinRecord<S> {
            if (!hasNext()) throw NoSuchElementException()
            return checkNotNull(pending).also { pending = null }
        }

        private fun findNext(): BuiltinRecord<S>? {
            while (frames.isNotEmpty()) {
                val frame = frames.last()
                if (!frame.children.hasNext()) {
                    frames.removeLast()
                } else {
                    visitChild(frame)?.let { return it }
                }
            }
            return null
        }

        private fun visitChild(frame: Frame<S>): BuiltinRecord<S>? {
            val (character, node) = frame.children.next()
            visitedNodes++
            val state = pattern.advance(frame.state, character)
            if (state.none { it }) return null
            frames.addLast(Frame(node.children.entries.iterator(), state))
            maxFrames = maxOf(maxFrames, frames.size)
            return node.record?.takeIf { pattern.accepts(state) }?.also { emittedRecords++ }
        }
    }

    private class Frame<S : ModelSubject>(
        val children: Iterator<Map.Entry<Char, Node<S>>>,
        val state: BooleanArray,
    )
}
