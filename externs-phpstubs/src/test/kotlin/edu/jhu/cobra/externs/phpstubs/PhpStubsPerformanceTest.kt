package edu.jhu.cobra.externs.phpstubs

import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test

/**
 * Tests for [PhpStubs] performance characteristics.
 *
 * - `function throughput - known functions` — measures lookup speed for declared functions
 * - `function throughput - unknown functions` — measures lookup speed for missing names
 * - `function throughput - keywords` — measures lookup speed for keyword functions
 * - `function throughput - uppercase input` — measures the folding overhead for uppercase
 * - `function throughput - namespace prefix input` — measures the spelling overhead for a leading backslash
 * - `clazz throughput - known classes` — measures lookup speed for declared classes
 * - `clazz throughput - scalar types` — measures lookup speed for scalar type names
 * - `method throughput - qualified spelling` — measures method lookup by `Owner::name`
 * - `method throughput - owner and name` — measures method lookup by split owner and name
 * - `constant throughput` — measures global constant lookup speed
 * - `memory footprint of the bundled merge` — reports heap usage after the bundled merge is built
 */
@Tag("performance")
internal class PhpStubsPerformanceTest {
    private val warmupRuns = 5
    private val measureRuns = 7

    private val knownFuncs = listOf("strlen", "substr", "array_map", "preg_match", "json_encode")
    private val unknownFuncs = listOf("nonexistent_aaa", "nonexistent_bbb", "nonexistent_ccc")
    private val keywordFuncs = listOf("echo", "isset", "require", "include_once", "print")
    private val knownClasses = listOf("exception", "stdclass", "pdo", "datetime", "arrayobject")
    private val scalarTypes = listOf("int", "float", "string", "bool", "array")
    private val qualifiedMethods = listOf("mysqli::query", "PDO::prepare", "DateTime::format")
    private val splitMethods = listOf("mysqli" to "query", "pdo" to "prepare", "datetime" to "format")
    private val constants = listOf("PHP_EOL", "PHP_INT_MAX", "E_ALL", "SORT_REGULAR", "M_PI")

    private val iterationsPerRun = 100_000

    @Test
    fun `function throughput - known functions`() = benchmark("function-known") { i -> PhpStubs.function(knownFuncs[i % knownFuncs.size]) }

    @Test
    fun `function throughput - unknown functions`() =
        benchmark("function-unknown") { i -> PhpStubs.function(unknownFuncs[i % unknownFuncs.size]) }

    @Test
    fun `function throughput - keywords`() = benchmark("function-keyword") { i -> PhpStubs.function(keywordFuncs[i % keywordFuncs.size]) }

    @Test
    fun `function throughput - uppercase input`() {
        val uppercase = knownFuncs.map { it.uppercase() }
        benchmark("function-uppercase") { i -> PhpStubs.function(uppercase[i % uppercase.size]) }
    }

    @Test
    fun `function throughput - namespace prefix input`() {
        val qualified = knownFuncs.map { "\\$it" }
        benchmark("function-namespacePrefix") { i -> PhpStubs.function(qualified[i % qualified.size]) }
    }

    @Test
    fun `clazz throughput - known classes`() = benchmark("clazz-known") { i -> PhpStubs.clazz(knownClasses[i % knownClasses.size]) }

    @Test
    fun `clazz throughput - scalar types`() = benchmark("clazz-scalar") { i -> PhpStubs.clazz(scalarTypes[i % scalarTypes.size]) }

    @Test
    fun `method throughput - qualified spelling`() =
        benchmark("method-qualified") { i -> PhpStubs.method(qualifiedMethods[i % qualifiedMethods.size]) }

    @Test
    fun `method throughput - owner and name`() =
        benchmark("method-split") { i ->
            val (owner, name) = splitMethods[i % splitMethods.size]
            PhpStubs.method(owner, name)
        }

    @Test
    fun `constant throughput`() = benchmark("constant") { i -> PhpStubs.constant(constants[i % constants.size]) }

    @Test
    fun `memory footprint of the bundled merge`() {
        val counts =
            mapOf(
                "functions" to PhpStubs.functions.size,
                "classes" to PhpStubs.classes.size,
                "methods" to PhpStubs.methods.size,
                "constants" to PhpStubs.constants.size,
                "facts" to
                    PhpStubs.sinks.size + PhpStubs.sources.size + PhpStubs.sanitizers.size + PhpStubs.flows.size + PhpStubs.returns.size,
            )
        val runtime = Runtime.getRuntime()
        runtime.gc()
        Thread.sleep(100)
        val used = runtime.totalMemory() - runtime.freeMemory()
        println("[memory-loaded] heap used after the bundled merge: %,d bytes (%.2f MB)".format(used, used / 1_048_576.0))
        for ((kind, count) in counts) println("[memory-loaded] $kind: %,d".format(count))
    }

    private fun benchmark(
        label: String,
        block: (Int) -> Any?,
    ) {
        val run = { repeat(iterationsPerRun) { i -> block(i) } }
        repeat(warmupRuns) { run() }
        val timesMs =
            (1..measureRuns).map {
                val start = System.nanoTime()
                run()
                (System.nanoTime() - start) / 1_000_000.0
            }
        val sorted = timesMs.sorted()
        val median = sorted[sorted.size / 2]
        val throughput = (iterationsPerRun / (median / 1_000.0)).toLong()
        val nsPerOp = median * 1_000_000.0 / iterationsPerRun
        println(
            "[$label] median=%.2f ms, avg=%.2f ms, min=%.2f ms, max=%.2f ms | %,d ops/s | %.1f ns/op"
                .format(median, timesMs.average(), timesMs.min(), timesMs.max(), throughput, nsPerOp),
        )
    }
}
