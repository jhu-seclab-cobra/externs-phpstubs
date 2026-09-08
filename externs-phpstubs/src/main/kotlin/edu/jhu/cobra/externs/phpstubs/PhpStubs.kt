package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.CategoryMappingLoader
import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.ModelSubject
import edu.jhu.cobra.commons.phpmodels.PropertySubject
import edu.jhu.cobra.commons.phpmodels.ResourceOpener
import edu.jhu.cobra.commons.phpmodels.TaintPolicy
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import edu.jhu.cobra.commons.phpmodels.Vocabulary
import java.nio.file.Files
import java.nio.file.Path

// The bundled merge: built on the first access to PhpStubs and shared by every later lookup.
private val bundled: PhpStubs = PhpStubs(bundledMounts())

// Merge order: generated declarations, value rules, canonical vocabulary, taint (mapped), taint rules (mapped).
private fun bundledMounts(): List<Mount> {
    val mapping =
        StubResources::class.java.getResourceAsStream(StubResources.PSALM_MAPPING)?.use(CategoryMappingLoader::load)
            ?: throw StubIndexNotFoundException(StubResources.PSALM_MAPPING)
    return MountSequence()
        .mount(StubResources.MODELS, StubResources.opener(StubResources.MODELS), fallback = null, corpus = true)
        .mount(StubResources.VALUE_RULES, StubResources.opener(StubResources.VALUE_RULES), fallback = null)
        .mount(StubResources.VOCABULARY, StubResources.opener(StubResources.VOCABULARY), fallback = null)
        .mount(StubResources.TAINT, StubResources.opener(StubResources.TAINT), mapping, fallback = null)
        .mount(StubResources.TAINT_RULES, StubResources.opener(StubResources.TAINT_RULES), mapping, fallback = null)
        .toList()
}

/**
 * One [BuiltinLookup] over one merge of document sets. The companion is the lookup over the bundled sets,
 * so `PhpStubs.function("substr")` reads the bundled merge; [with] and [plus] build a second lookup that
 * mounts extension sets after the bundled ones, leaving the receiver unchanged.
 *
 * Every bundled-set error surfaces on the first access to this class; an extension-set error surfaces
 * from the call that mounts it.
 */
public class PhpStubs internal constructor(
    private val mounts: List<Mount>,
) : BuiltinLookup {
    private val merge = Merge.of(mounts)

    override fun function(name: String): BuiltinRecord<FunctionSubject>? = merge.functions[FunctionSubject.parse(name)]

    override fun clazz(name: String): BuiltinRecord<ClassSubject>? = merge.classes[ClassSubject.parse(name)]

    override fun method(spelling: String): BuiltinRecord<MethodSubject>? = merge.methods[MethodSubject.parse(spelling)]

    override fun method(
        owner: String,
        name: String,
    ): BuiltinRecord<MethodSubject>? = merge.methods[MethodSubject(ClassSubject.parse(owner).name, name)]

    override fun constant(name: String): BuiltinRecord<ConstantSubject>? = merge.constants[ConstantSubject.parse(name)]

    override fun classConstant(spelling: String): BuiltinRecord<ClassConstantSubject>? =
        merge.classConstants[ClassConstantSubject.parse(spelling)]

    override fun classConstant(
        owner: String,
        name: String,
    ): BuiltinRecord<ClassConstantSubject>? = merge.classConstants[ClassConstantSubject(ClassSubject.parse(owner).name, name)]

    override fun property(spelling: String): BuiltinRecord<PropertySubject>? = merge.properties[PropertySubject.parse(spelling)]

    override fun property(
        owner: String,
        name: String,
    ): BuiltinRecord<PropertySubject>? = merge.properties[PropertySubject(ClassSubject.parse(owner).name, name)]

    override fun variable(name: String): BuiltinRecord<VariableSubject>? = merge.variables[VariableSubject.parse(name)]

    override fun record(subject: ModelSubject): BuiltinRecord<ModelSubject>? = merge.records[subject]

    override val functions: Collection<BuiltinRecord<FunctionSubject>> get() = merge.functions.values

    override val classes: Collection<BuiltinRecord<ClassSubject>> get() = merge.classes.values

    override val methods: Collection<BuiltinRecord<MethodSubject>> get() = merge.methods.values

    override val constants: Collection<BuiltinRecord<ConstantSubject>> get() = merge.constants.values

    override val classConstants: Collection<BuiltinRecord<ClassConstantSubject>> get() = merge.classConstants.values

    override val properties: Collection<BuiltinRecord<PropertySubject>> get() = merge.properties.values

    override val variables: Collection<BuiltinRecord<VariableSubject>> get() = merge.variables.values

    override val sinks: List<SinkFact> get() = merge.sinks

    override val sources: List<SourceFact> get() = merge.sources

    override val sanitizers: List<SanitizerFact> get() = merge.sanitizers

    override val flows: List<FlowFact> get() = merge.flows

    override val returns: List<ReturnsFact> get() = merge.returns

    override val vocabulary: Vocabulary get() = merge.vocabulary

    override val policy: TaintPolicy get() = merge.policy

    /**
     * A lookup that mounts the extension sets under the classpath [roots], in order, after this lookup's sets.
     *
     * @param roots Classpath directories each holding a manifest; a set without `provenance.yaml` mounts as manual.
     * @throws StubIndexNotFoundException If a manifest or a listed document is absent.
     * @throws StubIndexInvalidException If a set fails to load otherwise.
     */
    public fun with(vararg roots: String): PhpStubs = extend(roots.map { StubResources.normalize(it) to StubResources.opener(it) })

    /**
     * A lookup that mounts the extension sets under the filesystem [dirs], in order, after this lookup's sets.
     *
     * @param dirs Directories each holding a manifest; a set without `provenance.yaml` mounts as manual.
     * @throws StubIndexNotFoundException If a manifest or a listed document is absent.
     * @throws StubIndexInvalidException If a set fails to load otherwise.
     */
    public fun with(vararg dirs: Path): PhpStubs = extend(dirs.map { "$it/" to directoryOpener(it) })

    /** [with] of one classpath root. */
    public operator fun plus(root: String): PhpStubs = with(root)

    /** [with] of one directory. */
    public operator fun plus(dir: Path): PhpStubs = with(dir)

    private fun extend(sets: List<Pair<String, ResourceOpener>>): PhpStubs {
        val sequence = MountSequence(mounts)
        for ((label, open) in sets) sequence.mount(label, open)
        return PhpStubs(sequence.toList())
    }

    private fun directoryOpener(dir: Path): ResourceOpener =
        ResourceOpener { path ->
            val file = dir.resolve(path)
            if (Files.isRegularFile(file)) Files.newInputStream(file) else null
        }

    /** The lookup over the bundled sets; [with] and [plus] extend it. */
    public companion object : BuiltinLookup by bundled {
        /** [PhpStubs.with] over the bundled lookup. */
        public fun with(vararg roots: String): PhpStubs = bundled.with(*roots)

        /** [PhpStubs.with] over the bundled lookup. */
        public fun with(vararg dirs: Path): PhpStubs = bundled.with(*dirs)

        /** [PhpStubs.plus] over the bundled lookup. */
        public operator fun plus(root: String): PhpStubs = bundled + root

        /** [PhpStubs.plus] over the bundled lookup. */
        public operator fun plus(dir: Path): PhpStubs = bundled + dir
    }
}
