package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.VariableSubject
import edu.jhu.cobra.commons.phpmodels.VulnTypeId
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * Tests for the data of scheme injection in the merged bundled sets.
 *
 * - `every output sink of cross-site scripting has a scheme injection twin` — verifies equal ports per owner and condition
 * - `a value transform covers scheme injection when it covers every other type` — verifies the all-types transforms
 * - `escapes cover scheme injection exactly when they encode the characters that fix a scheme` — verifies the named lists
 * - `the server superglobal splits on the keys that hold the request path` — verifies the two source facts
 * - `the policy keeps path-derived values out of scheme injection` — verifies the matrix through the lookup
 */
internal class SchemeDataTest {
    private val scheme = VulnType.SCHEMEI.id

    private fun coveredBy(name: String): List<Set<VulnTypeId>> =
        PhpStubs.sanitizerFacts.filter { it.owner == FunctionSubject(name) }.map { it.vulnTypes }

    @Test
    fun `every output sink of cross-site scripting has a scheme injection twin`() {
        val ports = PhpStubs.sinkFacts.groupBy({ it.owner to it.condition }, { it.port to it.vulnType })
        val twinned = ports.filterValues { points -> points.any { it.second == VulnType.XSS.id } }
        assertTrue(FunctionSubject("echo") to null in twinned)
        assertTrue(FunctionSubject("print_r") to null in twinned)
        for ((unit, points) in twinned) {
            val html = points.filter { it.second == VulnType.XSS.id }.map { it.first }.toSet()
            val link = points.filter { it.second == scheme }.map { it.first }.toSet()
            assertEquals(html, link, "${unit.first}")
        }
    }

    @Test
    fun `a value transform covers scheme injection when it covers every other type`() {
        val others = VulnType.entries.map { it.id }.toSet() - scheme
        val whole = PhpStubs.sanitizerFacts.filter { it.condition == null && it.vulnTypes.containsAll(others) }
        assertTrue(whole.map { it.owner }.toSet().containsAll(listOf("intval", "floatval", "md5").map(FunctionSubject::parse)))
        for (fact in whole) {
            assertTrue(scheme in fact.vulnTypes, "${fact.owner}")
        }
    }

    @Test
    fun `escapes cover scheme injection exactly when they encode the characters that fix a scheme`() {
        for (name in listOf("urlencode", "rawurlencode", "curl_escape", "intval", "floatval")) {
            assertTrue(coveredBy(name).any { scheme in it }, name)
        }
        for (name in listOf("htmlspecialchars", "htmlentities", "strip_tags", "filter_var", "addslashes", "basename")) {
            assertTrue(coveredBy(name).none { scheme in it }, name)
        }
        assertTrue(coveredBy("urlencode").any { VulnType.XSS.id in it && scheme in it })
    }

    @Test
    fun `the server superglobal splits on the keys that hold the request path`() {
        val facts = PhpStubs.sourceFacts.filter { it.owner == VariableSubject("_SERVER") }
        assertEquals(2, facts.size)
        val path = facts.single { it.sourceKinds == setOf(SourceKind.SERVER_PATH.id) }
        val rest = facts.single { it.sourceKinds == setOf(SourceKind.USER_INPUT.id) }
        assertEquals(listOf("PHP_SELF", "REQUEST_URI", "SCRIPT_NAME", "PATH_INFO"), path.keys!!.map { it.pattern })
        val pathKeys = listOf("PHP_SELF", "REQUEST_URI", "SCRIPT_NAME", "PATH_INFO")
        val otherKeys = listOf("HTTP_REFERER", "QUERY_STRING", "HTTP_HOST", "REQUEST_METHOD", "HTTP_USER_AGENT", "path_info", "PATH_INFO_X")
        for (key in pathKeys) {
            assertTrue(path.keys!!.any { it.matches(key) } && rest.keys!!.none { it.matches(key) }, key)
        }
        for (key in otherKeys) {
            assertTrue(path.keys!!.none { it.matches(key) } && rest.keys!!.any { it.matches(key) }, key)
        }
    }

    @Test
    fun `the policy keeps path-derived values out of scheme injection`() {
        val path = SourceKind.SERVER_PATH.id
        assertFalse(PhpStubs.policy.isDangerous(path, scheme))
        for (type in VulnType.entries - VulnType.SCHEMEI) {
            assertTrue(PhpStubs.policy.isDangerous(path, type.id), type.id.id)
        }
        for (kind in listOf(SourceKind.USER_INPUT, SourceKind.EXTERNAL_INPUT)) {
            assertTrue(PhpStubs.policy.isDangerous(kind.id, scheme), kind.id.id)
        }
    }
}
