package edu.jhu.cobra.externs.phpstubs

import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test

/**
 * Tests for [PhpStubs] performance characteristics.
 *
 * - `containsFunction throughput - known functions` — measures lookup speed for registered functions
 * - `containsFunction throughput - unknown functions` — measures lookup speed for missing names
 * - `containsFunction throughput - keywords` — measures lookup speed for keyword functions
 * - `containsClass throughput - known classes` — measures lookup speed for registered classes
 * - `containsClass throughput - scalar types` — measures lookup speed for scalar type names
 * - `containsMethod throughput - with class name` — measures method lookup with owning class
 * - `containsMethod throughput - suffix only` — measures method lookup by name suffix
 * - `containsConstant throughput` — measures constant lookup speed
 * - `findFunction throughput - known functions` — measures entry retrieval for registered functions
 * - `findFunction throughput - keywords` — measures entry retrieval for keyword functions
 * - `findClass throughput - scalar types` — measures entry retrieval for scalar types
 * - `findMethod throughput - with class name` — measures method entry retrieval with class
 * - `findMethod throughput - suffix only` — measures method entry retrieval by suffix
 * - `containsFunction throughput - uppercase input` — measures normalization overhead for uppercase
 * - `containsFunction throughput - namespace prefix input` — measures spelling overhead for a leading backslash
 * - `memory footprint of loaded registry` — reports heap usage after full data load
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
    private val knownMethods =
        listOf(
            "query" to "mysqli",
            "prepare" to "pdo",
            "format" to "datetime",
        )
    private val suffixOnlyMethods = listOf("query", "prepare", "format", "getcode", "getmessage")

    private val iterationsPerRun = 100_000

    // -- Hot path: existence checks --

    @Test
    fun `containsFunction throughput - known functions`() {
        benchmarkOps("containsFunction-known", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunction(knownFuncs[i % knownFuncs.size])
            }
        }
    }

    @Test
    fun `containsFunction throughput - unknown functions`() {
        benchmarkOps("containsFunction-unknown", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunction(unknownFuncs[i % unknownFuncs.size])
            }
        }
    }

    @Test
    fun `containsFunction throughput - keywords`() {
        benchmarkOps("containsFunction-keyword", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunction(keywordFuncs[i % keywordFuncs.size])
            }
        }
    }

    @Test
    fun `containsClass throughput - known classes`() {
        benchmarkOps("containsClass-known", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsClass(knownClasses[i % knownClasses.size])
            }
        }
    }

    @Test
    fun `containsClass throughput - scalar types`() {
        benchmarkOps("containsClass-scalar", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsClass(scalarTypes[i % scalarTypes.size])
            }
        }
    }

    @Test
    fun `containsMethod throughput - with class name`() {
        benchmarkOps("containsMethod-withClass", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                val (method, cls) = knownMethods[i % knownMethods.size]
                PhpStubs.containsMethod(method, cls)
            }
        }
    }

    @Test
    fun `containsMethod throughput - suffix only`() {
        benchmarkOps("containsMethod-suffixOnly", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsMethod(suffixOnlyMethods[i % suffixOnlyMethods.size])
            }
        }
    }

    @Test
    fun `containsConstant throughput`() {
        val consts = listOf("PHP_EOL", "PHP_INT_MAX", "TRUE", "FALSE", "NULL")
        benchmarkOps("containsConstant", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsConstant(consts[i % consts.size])
            }
        }
    }

    // -- Cold path: entry retrieval --

    @Test
    fun `findFunction throughput - known functions`() {
        benchmarkOps("findFunction-known", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.findFunction(knownFuncs[i % knownFuncs.size])
            }
        }
    }

    @Test
    fun `findFunction throughput - keywords`() {
        benchmarkOps("findFunction-keyword", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.findFunction(keywordFuncs[i % keywordFuncs.size])
            }
        }
    }

    @Test
    fun `findClass throughput - scalar types`() {
        benchmarkOps("findClass-scalar", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.findClass(scalarTypes[i % scalarTypes.size])
            }
        }
    }

    @Test
    fun `findMethod throughput - with class name`() {
        benchmarkOps("findMethod-withClass", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                val (method, cls) = knownMethods[i % knownMethods.size]
                PhpStubs.findMethod(method, cls)
            }
        }
    }

    @Test
    fun `findMethod throughput - suffix only`() {
        benchmarkOps("findMethod-suffixOnly", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.findMethod(suffixOnlyMethods[i % suffixOnlyMethods.size])
            }
        }
    }

    // -- Spelling edge cases --

    @Test
    fun `containsFunction throughput - uppercase input`() {
        val uppercaseFuncs = knownFuncs.map { it.uppercase() }
        benchmarkOps("containsFunction-uppercase", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunction(uppercaseFuncs[i % uppercaseFuncs.size])
            }
        }
    }

    @Test
    fun `containsFunction throughput - namespace prefix input`() {
        val qualifiedFuncs = knownFuncs.map { "\\$it" }
        benchmarkOps("containsFunction-namespacePrefix", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunction(qualifiedFuncs[i % qualifiedFuncs.size])
            }
        }
    }

    // -- Memory --

    @Test
    fun `memory footprint of loaded registry`() {
        // Force full load
        PhpStubs.functionNames
        PhpStubs.classNames
        PhpStubs.methodNames
        PhpStubs.constantNames

        val runtime = Runtime.getRuntime()
        runtime.gc()
        Thread.sleep(100)
        val used = runtime.totalMemory() - runtime.freeMemory()
        println("[memory-loaded] heap used after full load: %,d bytes (%.2f MB)".format(used, used / 1_048_576.0))
        println("[memory-loaded] functions: %,d keys".format(PhpStubs.functionNames.size))
        println("[memory-loaded] classes: %,d keys".format(PhpStubs.classNames.size))
        println("[memory-loaded] methods: %,d keys".format(PhpStubs.methodNames.size))
        println("[memory-loaded] constants: %,d keys".format(PhpStubs.constantNames.size))
    }

    // -- Helpers --

    private fun benchmarkOps(
        label: String,
        opsPerRun: Long,
        block: () -> Unit,
    ) {
        // warmup
        repeat(warmupRuns) { block() }

        // measure
        val timesMs =
            (1..measureRuns).map {
                val start = System.nanoTime()
                block()
                (System.nanoTime() - start) / 1_000_000.0
            }

        val sorted = timesMs.sorted()
        val median = sorted[sorted.size / 2]
        val avg = timesMs.average()
        val min = timesMs.min()
        val max = timesMs.max()
        val throughput = (opsPerRun / (median / 1_000.0)).toLong()
        val nsPerOp = median * 1_000_000.0 / opsPerRun

        println(
            "[$label] median=%.2f ms, avg=%.2f ms, min=%.2f ms, max=%.2f ms | %,d ops/s | %.1f ns/op"
                .format(median, avg, min, max, throughput, nsPerOp),
        )
    }
}
