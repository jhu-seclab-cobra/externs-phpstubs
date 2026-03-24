package edu.jhu.cobra.externs.phpstubs

import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test

@Tag("performance")
class PhpStubsPerformanceTest {

    private val warmupRuns = 5
    private val measureRuns = 7

    private val knownFuncs = listOf("strlen", "substr", "array_map", "preg_match", "json_encode")
    private val unknownFuncs = listOf("nonexistent_aaa", "nonexistent_bbb", "nonexistent_ccc")
    private val keywordFuncs = listOf("echo", "isset", "require", "include_once", "print")
    private val knownClasses = listOf("exception", "stdclass", "pdo", "datetime", "arrayobject")
    private val scalarTypes = listOf("int", "float", "string", "bool", "array")
    private val knownMethods = listOf(
        "query" to "mysqli",
        "prepare" to "pdo",
        "format" to "datetime",
    )
    private val suffixOnlyMethods = listOf("query", "prepare", "format", "getcode", "getmessage")

    private val iterationsPerRun = 100_000

    // -- Hot path: existence checks --

    @Test
    fun `containsFunc throughput - known functions`() {
        benchmarkOps("containsFunc-known", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunc(knownFuncs[i % knownFuncs.size])
            }
        }
    }

    @Test
    fun `containsFunc throughput - unknown functions`() {
        benchmarkOps("containsFunc-unknown", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunc(unknownFuncs[i % unknownFuncs.size])
            }
        }
    }

    @Test
    fun `containsFunc throughput - keywords`() {
        benchmarkOps("containsFunc-keyword", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunc(keywordFuncs[i % keywordFuncs.size])
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
    fun `containsConst throughput`() {
        val consts = listOf("php_eol", "php_int_max", "true", "false", "null")
        benchmarkOps("containsConst", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsConst(consts[i % consts.size])
            }
        }
    }

    // -- Cold path: record retrieval --

    @Test
    fun `searchFunc throughput - known functions`() {
        benchmarkOps("searchFunc-known", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.searchFunc(knownFuncs[i % knownFuncs.size])
            }
        }
    }

    @Test
    fun `searchFunc throughput - keywords`() {
        benchmarkOps("searchFunc-keyword", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.searchFunc(keywordFuncs[i % keywordFuncs.size])
            }
        }
    }

    @Test
    fun `searchClass throughput - scalar types`() {
        benchmarkOps("searchClass-scalar", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.searchClass(scalarTypes[i % scalarTypes.size])
            }
        }
    }

    @Test
    fun `searchMethod throughput - with class name`() {
        benchmarkOps("searchMethod-withClass", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                val (method, cls) = knownMethods[i % knownMethods.size]
                PhpStubs.searchMethod(method, cls)
            }
        }
    }

    @Test
    fun `searchMethod throughput - suffix only`() {
        benchmarkOps("searchMethod-suffixOnly", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.searchMethod(suffixOnlyMethods[i % suffixOnlyMethods.size])
            }
        }
    }

    // -- Normalize edge cases --

    @Test
    fun `containsFunc throughput - uppercase input`() {
        val uppercaseFuncs = knownFuncs.map { it.uppercase() }
        benchmarkOps("containsFunc-uppercase", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunc(uppercaseFuncs[i % uppercaseFuncs.size])
            }
        }
    }

    @Test
    fun `containsFunc throughput - slash prefix input`() {
        val slashFuncs = knownFuncs.map { "/$it" }
        benchmarkOps("containsFunc-slashPrefix", iterationsPerRun.toLong()) {
            repeat(iterationsPerRun) { i ->
                PhpStubs.containsFunc(slashFuncs[i % slashFuncs.size])
            }
        }
    }

    // -- Memory --

    @Test
    fun `memory footprint of loaded StubData`() {
        // Force full load
        PhpStubs.getAllFuncNames()
        PhpStubs.getAllClassNames()
        PhpStubs.getAllMethodNames()
        PhpStubs.getAllConstNames()

        val runtime = Runtime.getRuntime()
        runtime.gc(); Thread.sleep(100)
        val used = runtime.totalMemory() - runtime.freeMemory()
        println("[memory-loaded] heap used after full load: %,d bytes (%.2f MB)".format(used, used / 1_048_576.0))
        println("[memory-loaded] functions: %,d keys".format(PhpStubs.getAllFuncNames().size))
        println("[memory-loaded] classes: %,d keys".format(PhpStubs.getAllClassNames().size))
        println("[memory-loaded] methods: %,d keys".format(PhpStubs.getAllMethodNames().size))
        println("[memory-loaded] constants: %,d keys".format(PhpStubs.getAllConstNames().size))
    }

    // -- Helpers --

    private fun benchmarkOps(label: String, opsPerRun: Long, block: () -> Unit) {
        // warmup
        repeat(warmupRuns) { block() }

        // measure
        val timesMs = (1..measureRuns).map {
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
