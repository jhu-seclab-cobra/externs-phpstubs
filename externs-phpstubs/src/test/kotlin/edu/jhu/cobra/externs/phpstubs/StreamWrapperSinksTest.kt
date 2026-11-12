package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.Port
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import org.junit.jupiter.api.DynamicTest
import org.junit.jupiter.api.TestFactory

/** A path reader exposes both file access and a request through its stream wrapper. */
internal class StreamWrapperSinksTest {
    @TestFactory
    fun `file readers sink the path as file and ssrf`(): List<DynamicTest> {
        val functions = listOf(
            "exif_imagetype" to 0,
            "exif_read_data" to 0,
            "exif_thumbnail" to 0,
            "md5_file" to 0,
            "sha1_file" to 0,
            "gzfile" to 0,
            "mime_content_type" to 0,
            "imageloadfont" to 0,
            "file_get_contents" to 0,
            "fopen" to 0,
            "file" to 0,
            "copy" to 0,
            "bzopen" to 0,
            "gzopen" to 0,
            "readgzfile" to 0,
            "get_meta_tags" to 0,
            "getimagesize" to 0,
            "highlight_file" to 0,
            "show_source" to 0,
            "parse_ini_file" to 0,
            "php_strip_whitespace" to 0,
            "imagecreatefromxpm" to 0,
            "imagecreatefromgif" to 0,
            "imagecreatefromjpeg" to 0,
            "imagecreatefrompng" to 0,
            "imagecreatefromwebp" to 0,
            "imagecreatefrombmp" to 0,
            "imagecreatefromavif" to 0,
            "imagecreatefromwbmp" to 0,
            "imagecreatefromxbm" to 0,
            "imagecreatefromtga" to 0,
            "imagecreatefromgd" to 0,
            "imagecreatefromgd2" to 0,
            "imagecreatefromgd2part" to 0,
            "hash_file" to 1,
            "hash_hmac_file" to 1,
            "hash_update_file" to 1,
            "finfo_file" to 1,
        )
        return functions.map { (name, port) ->
            DynamicTest.dynamicTest(name) {
                assertPathSinks(assertNotNull(PhpStubs.function(name)).sinkFacts, port)
            }
        } + listOf("finfo::file", "SplFileObject::__construct").map { name ->
            DynamicTest.dynamicTest(name) {
                assertPathSinks(assertNotNull(PhpStubs.method(name)).sinkFacts, 0)
            }
        }
    }

    private fun assertPathSinks(facts: List<SinkFact>, port: Int) {
        val pathFacts = facts.filter { it.port == Port.Argument(port) }
        val kinds = pathFacts.map { it.vulnType }.toSet()
        assertEquals(setOf(VulnType.PATHTRAV.id, VulnType.SSRF.id), kinds - VulnType.XSS.id)
        pathFacts.forEach { assertNull(it.condition) }
    }
}
