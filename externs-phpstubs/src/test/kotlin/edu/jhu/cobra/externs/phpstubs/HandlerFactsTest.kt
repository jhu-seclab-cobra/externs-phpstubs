package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.Classifier
import edu.jhu.cobra.commons.phpmodels.HandlerRequest
import edu.jhu.cobra.commons.phpmodels.HandlerRequest.IS_ARRAY
import edu.jhu.cobra.commons.phpmodels.HandlerRequest.IS_DOUBLE
import edu.jhu.cobra.commons.phpmodels.HandlerRequest.IS_LONG
import edu.jhu.cobra.commons.phpmodels.HandlerRequest.IS_RESOURCE
import edu.jhu.cobra.commons.phpmodels.HandlerRequest.IS_STRING
import edu.jhu.cobra.commons.phpmodels.HandlerRequest.ZEND_BOOL_NOT
import edu.jhu.cobra.commons.phpmodels.HandlerRequest._IS_BOOL
import edu.jhu.cobra.commons.phpmodels.HandlerRequest._IS_NUMBER
import edu.jhu.cobra.commons.phpmodels.HandlerSlot
import edu.jhu.cobra.commons.phpmodels.HandlerTable
import edu.jhu.cobra.commons.phpmodels.ReturnKind
import edu.jhu.cobra.commons.phpmodels.ReturnKind.ANY
import edu.jhu.cobra.commons.phpmodels.ReturnKind.BOOL
import edu.jhu.cobra.commons.phpmodels.ReturnKind.NUM
import edu.jhu.cobra.commons.phpmodels.ReturnKind.STR
import edu.jhu.cobra.commons.phpmodels.StringDispatch
import edu.jhu.cobra.commons.phpmodels.StringDispatch.METHOD_FIRST
import edu.jhu.cobra.commons.phpmodels.StringDispatch.METHOD_ONLY
import edu.jhu.cobra.commons.phpmodels.StringDispatch.NATIVE_FIRST
import edu.jhu.cobra.commons.phpmodels.StringDispatch.NONE
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for the handler facts and finality of the bundled class records (design-extraction-handlers.md,
 * spec-extraction-handlers.md). The expectations are read off php-src 8.5 and its PHP 8.5.12 behavior, never off the
 * extractor's output; each mapping test cites the C function it follows and the reference programs it pins.
 *
 * Coverage of the generated documents:
 * - `the manifest lists 56 documents and 310 subjects` -- the inventory of class and enum entries
 * - `every manifest document is a bundled model document` -- each file loads from the bundled models
 * - `every manifest subject is a class or enum record with a classifier` -- 310 records
 * - `registered classes carry handler tables and finality, enums and unregistered classes carry none`
 * - `the unregistered classes keep only their classifier` -- two PDO pseudo-classes, five external classes
 * - `every table names its source and answers every request` -- complete coverage of the delivered tables
 * - `registered enums and interfaces keep their registered flags` -- finality is the registration flag only
 *
 * Mappings:
 * - `standard objects use the standard table` -- stdClass, Exception (probes null_and_missing, standard_descendant)
 * - `SimpleXML consults the method first for a string and keeps the other casts native` -- inherited_string
 * - `tidy converts natively and never calls the method` -- tidy_override, throwing_dispatch
 * - `COM converts natively first and falls back to the standard conversion` -- source and fixture only
 * - `BcMath number operates on arithmetic opcodes only` -- native_operator_result
 * - `GMP operations answer an object and the other opcodes fail` -- constant_requests, bool_not_initializer
 * - `DateTime overrides only the comparison` -- compare_only_string, J-compare-only
 * - `FFI keeps one table per object state` -- table_alternatives, J-FFI-instance, J-FFI-numeric
 * - `final native classes are final and open ones are not` -- final_classes, finality_independent
 */
internal class HandlerFactsTest {
    private val manifest: Map<String, List<String>> = readManifest()
    private val subjects: List<String> = manifest.values.flatten()

    // ========== coverage of the generated documents ==========

    @Test
    fun `the manifest lists 56 documents and 310 subjects`() {
        assertEquals(56, manifest.size)
        assertEquals(310, subjects.size)
        assertEquals(310, subjects.toSet().size)
    }

    @Test
    fun `every manifest document is a bundled model document`() {
        val opener = StubResources.opener(StubResources.MODELS)
        for (document in manifest.keys) {
            assertNotNull(opener.open(document), document).close()
        }
    }

    @Test
    fun `every manifest subject is a class or enum record with a classifier`() {
        for (name in subjects) {
            val classifier = signatureOf(name).classifier
            assertTrue(classifier == Classifier.CLASS || classifier == Classifier.ENUM, "$name: $classifier")
        }
    }

    @Test
    fun `registered classes carry handler tables and finality, enums and unregistered classes carry none`() {
        val withTables = subjects.filter { signatureOf(it).handlers.isNotEmpty() }
        val registered = subjects.filter { signatureOf(it).classifier == Classifier.CLASS && it !in PSEUDO }
        assertEquals(registered.toSet(), withTables.toSet())
        assertEquals(301, withTables.size)
        for (name in registered) assertNotNull(signatureOf(name).isFinal, name)
        for (name in subjects.filter { signatureOf(it).classifier == Classifier.ENUM }) {
            assertTrue(signatureOf(name).handlers.isEmpty(), name)
        }
    }

    @Test
    fun `the unregistered classes keep only their classifier`() {
        for (name in PSEUDO + EXTERNAL) {
            val signature = signatureOf(name)
            assertEquals(Classifier.CLASS, signature.classifier, name)
            assertNull(signature.parent, name)
            assertTrue(signature.interfaces.isEmpty(), name)
            assertNull(signature.isFinal, name)
            assertTrue(signature.handlers.isEmpty(), name)
        }
    }

    @Test
    fun `every table names its source and answers every request`() {
        val everyCast = HandlerRequest.entries.filter { it.slot == HandlerSlot.CAST }
        val everyOperation = HandlerRequest.entries.filter { it.slot == HandlerSlot.OPERATION }
        for (name in subjects) {
            for (table in signatureOf(name).handlers) {
                assertTrue(SOURCE_SYMBOL.matches(table.id), "$name: ${table.id}")
                table.facts.flatMap { it.targets }.forEach { assertTrue(SOURCE_SYMBOL.matches(it.symbol), it.symbol) }
                assertSlotComplete(table, HandlerSlot.CAST, everyCast.toSet())
                assertSlotComplete(table, HandlerSlot.COMPARE, setOf(null))
                assertSlotComplete(table, HandlerSlot.OPERATION, everyOperation.toSet())
            }
        }
    }

    @Test
    fun `registered enums and interfaces keep their registered flags`() {
        for (name in listOf("roundingmode", "propertyhooktype", "dom\\adjacentposition", "uri\\uricomparisonmode")) {
            val signature = signatureOf(name)
            assertEquals(Classifier.ENUM, signature.classifier, name)
            assertEquals(false, signature.isFinal, name)
        }
        for (name in listOf("stringable", "iterator", "throwable", "traversable")) {
            val signature = signatureOf(name)
            assertEquals(Classifier.INTERFACE, signature.classifier, name)
            assertEquals(false, signature.isFinal, name)
            assertTrue(signature.handlers.isEmpty(), name)
        }
    }

    // ========== standard objects ==========

    // Zend/zend_object_handlers.c: zend_std_cast_object_tostring answers a string only through the method and the
    // boolean cast with true; every other target fails. std_object_handlers.do_operation is NULL.
    @Test
    fun `standard objects use the standard table`() {
        val table = singleTable("stdclass")
        assertEquals("Zend/zend_object_handlers.c:std_object_handlers", table.id)
        assertCasts(table, STD_CAST, string = emptySet(), dispatch = METHOD_ONLY)
        assertCompare(table, "Zend/zend_object_handlers.c:zend_std_compare_objects")
        assertOperationsAbsent(table)
        assertEquals(false, signatureOf("stdclass").isFinal)
        assertNull(signatureOf("stdclass").parent)
    }

    // Zend/zend_exceptions.c: the exception classes have their own table, which copies the standard one; Exception has
    // a native __toString, so its string conversion can produce a string.
    @Test
    fun `exception classes share the exception table with the standard cast`() {
        val table = singleTable("exception")
        assertEquals("Zend/zend_exceptions.c:default_exception_handlers", table.id)
        assertCasts(table, STD_CAST, string = setOf(STR, ANY), dispatch = METHOD_ONLY)
        assertCompare(table, "Zend/zend_object_handlers.c:zend_std_compare_objects")
        assertOperationsAbsent(table)
        assertEquals(table.id, singleTable("typeerror").id)
        assertEquals("error", signatureOf("typeerror").parent)
    }

    // ========== SimpleXML ==========

    // ext/simplexml/simplexml.c:1903-1912: sxe_object_cast calls the standard string conversion first, then the
    // native one. sxe_object_cast_ex: _IS_BOOL true or the property test, IS_LONG/IS_DOUBLE/_IS_NUMBER numbers,
    // IS_STRING a string, every other target fails. do_operation is NULL: `$x + 1` is int(5) (native_scalar_operator).
    @Test
    fun `SimpleXML consults the method first for a string and keeps the other casts native`() {
        val table = singleTable("simplexmlelement")
        assertEquals("ext/simplexml/simplexml.c:sxe_object_handlers", table.id)
        assertCasts(
            table,
            "ext/simplexml/simplexml.c:sxe_object_cast",
            string = setOf(STR, ANY),
            dispatch = METHOD_FIRST,
            numbers = setOf(NUM),
        )
        assertCompare(table, "ext/simplexml/simplexml.c:sxe_objects_compare")
        assertOperationsAbsent(table)
        assertEquals(false, signatureOf("simplexmlelement").isFinal)
        assertEquals(table.id, singleTable("simplexmliterator").id)
        assertEquals("simplexmlelement", signatureOf("simplexmliterator").parent)
    }

    // ========== tidy ==========

    // ext/tidy/tidy.c:416-490: tidy_doc_cast_handler and tidy_node_cast_handler write the native value for IS_STRING
    // without consulting a user method (tidy_override, throwing_dispatch); numbers are 0, _IS_BOOL is true.
    @Test
    fun `tidy converts natively and never calls the method`() {
        val document = singleTable("tidy")
        val node = singleTable("tidynode")
        assertEquals("ext/tidy/tidy.c:tidy_object_handlers_doc", document.id)
        assertEquals("ext/tidy/tidy.c:tidy_object_handlers_node", node.id)
        assertCasts(document, "ext/tidy/tidy.c:tidy_doc_cast_handler", string = setOf(STR), dispatch = NONE, numbers = setOf(NUM))
        assertCasts(node, "ext/tidy/tidy.c:tidy_node_cast_handler", string = setOf(STR), dispatch = NONE, numbers = setOf(NUM))
        assertCompare(document, "Zend/zend_object_handlers.c:zend_std_compare_objects")
        assertOperationsAbsent(document)
        assertOperationsAbsent(node)
        assertEquals(false, signatureOf("tidy").isFinal)
        assertEquals(true, signatureOf("tidynode").isFinal)
    }

    // ========== COM ==========

    // ext/com_dotnet/com_handlers.c:432-490: the converted variant is the result (its type is unknown to the class
    // fact) unless the conversion failed, and only then the standard conversion runs; the boolean cast then answers
    // true. COM is unavailable in the reference build (J-environment), so this mapping is source and fixture only.
    @Test
    fun `COM converts natively first and falls back to the standard conversion`() {
        val table = singleTable("variant")
        assertEquals("ext/com_dotnet/com_handlers.c:php_com_object_handlers", table.id)
        assertCasts(
            table,
            "ext/com_dotnet/com_handlers.c:com_object_cast",
            string = setOf(ANY),
            dispatch = NATIVE_FIRST,
            numbers = setOf(ANY),
            bool = setOf(BOOL, ANY),
            others = setOf(ANY),
        )
        assertCompare(table, "ext/com_dotnet/com_handlers.c:com_objects_compare")
        assertOperationsAbsent(table)
        for (name in listOf("com", "dotnet")) {
            assertEquals(table, singleTable(name), name)
            assertEquals("variant", signatureOf(name).parent, name)
        }
    }

    // ========== BcMath ==========

    // ext/bcmath/bcmath.c:1030-1039, 1255-1267: only _IS_BOOL is native, every other cast is the standard conversion;
    // do_operation answers ADD, SUB, MUL, DIV, MOD and POW with a number object and fails on every other opcode.
    @Test
    fun `BcMath number operates on arithmetic opcodes only`() {
        val table = singleTable("bcmath\\number")
        assertCasts(table, "ext/bcmath/bcmath.c:bcmath_number_cast_object", string = setOf(STR, ANY), dispatch = METHOD_ONLY)
        assertCompare(table, "ext/bcmath/bcmath.c:bcmath_number_compare")
        val arithmetic = setOf("ZEND_ADD", "ZEND_SUB", "ZEND_MUL", "ZEND_DIV", "ZEND_MOD", "ZEND_POW")
        assertOperations(table, "ext/bcmath/bcmath.c:bcmath_number_do_operation", arithmetic)
        assertEquals(true, signatureOf("bcmath\\number").isFinal)
    }

    // ========== GMP ==========

    // ext/gmp/gmp.c:236-267, 405-441: the casts produce numbers and a string; ADD, SUB, MUL, POW, DIV, MOD, SL, SR,
    // BW_OR, BW_AND, BW_XOR and BW_NOT produce a GMP object; CONCAT, BOOL_XOR and BOOL_NOT fail. The engine's `!` of
    // an object reads the boolean cast, not the operation (bool_not_initializer, constant_requests).
    @Test
    fun `GMP operations answer an object and the other opcodes fail`() {
        val table = singleTable("gmp")
        assertCasts(table, "ext/gmp/gmp.c:gmp_cast_object", string = setOf(STR), dispatch = NONE, numbers = setOf(NUM))
        assertCompare(table, "ext/gmp/gmp.c:gmp_compare")
        val objects = HandlerRequest.entries.filter { it.slot == HandlerSlot.OPERATION }.map { it.name }.toSet() -
            setOf("ZEND_CONCAT", "ZEND_BOOL_XOR", "ZEND_BOOL_NOT")
        assertOperations(table, "ext/gmp/gmp.c:gmp_do_operation", objects)
        val boolNot = table.facts.single { it.request == ZEND_BOOL_NOT }
        assertTrue(boolNot.targets.single().results.isEmpty())
        assertEquals(true, signatureOf("gmp").isFinal)
    }

    // ========== DateTime ==========

    // ext/date/php_date.c:1750-1770: only compare is replaced; DateTime and DateTimeImmutable both read
    // date_object_handlers_date; the numeric casts fail while the engine falls back to 1 with a diagnostic (J-compare-only).
    @Test
    fun `DateTime overrides only the comparison`() {
        val date = singleTable("datetime")
        assertEquals("ext/date/php_date.c:date_object_handlers_date", date.id)
        assertCasts(date, STD_CAST, string = emptySet(), dispatch = METHOD_ONLY)
        assertCompare(date, "ext/date/php_date.c:date_object_compare_date")
        assertOperationsAbsent(date)
        assertEquals(date, singleTable("datetimeimmutable"))
        assertEquals(false, signatureOf("datetimeimmutable").isFinal)
        assertEquals("ext/date/php_date.c:date_object_handlers_timezone", singleTable("datetimezone").id)
    }

    // ========== FFI ==========

    // ext/ffi/ffi.c:1863-1933, 5544-5592: a pointer or array CData has do_operation; a value CData and a freed CData
    // copy the standard table and leave it NULL; a freed CData converts through the fake cast, which fails on a string.
    @Test
    fun `FFI keeps one table per object state`() {
        val tables = tablesOf("ffi\\cdata").associateBy { it.id }
        assertEquals(
            setOf(
                "ext/ffi/ffi.c:zend_ffi_cdata_handlers",
                "ext/ffi/ffi.c:zend_ffi_cdata_value_handlers",
                "ext/ffi/ffi.c:zend_ffi_cdata_free_handlers",
            ),
            tables.keys,
        )
        val ordinary = tables.getValue("ext/ffi/ffi.c:zend_ffi_cdata_handlers")
        val value = tables.getValue("ext/ffi/ffi.c:zend_ffi_cdata_value_handlers")
        val freed = tables.getValue("ext/ffi/ffi.c:zend_ffi_cdata_free_handlers")
        val cast = "ext/ffi/ffi.c:zend_ffi_cdata_cast_object"
        assertCasts(ordinary, cast, string = setOf(STR), dispatch = NONE)
        assertCasts(value, cast, string = setOf(STR), dispatch = NONE)
        assertCasts(freed, "ext/ffi/ffi.c:zend_fake_cast_object", string = emptySet(), dispatch = NONE)
        val operation = "ext/ffi/ffi.c:zend_ffi_cdata_do_operation"
        assertOperations(ordinary, operation, setOf("ZEND_ADD"), numberOrObject = setOf("ZEND_SUB"))
        assertOperationsAbsent(value)
        assertOperationsAbsent(freed)
        for (table in listOf(ordinary, value, freed)) assertCompare(table, "ext/ffi/ffi.c:zend_ffi_cdata_compare_objects")
    }

    // ext/ffi/ffi.c: FFI and FFI\CType use the fake cast (a string fails, the boolean cast is true) and their own compare.
    @Test
    fun `FFI and its type objects convert through the fake cast`() {
        val ffi = singleTable("ffi")
        val type = singleTable("ffi\\ctype")
        assertCasts(ffi, "ext/ffi/ffi.c:zend_fake_cast_object", string = emptySet(), dispatch = NONE)
        assertCasts(type, "ext/ffi/ffi.c:zend_fake_cast_object", string = emptySet(), dispatch = NONE)
        assertCompare(ffi, "ext/ffi/ffi.c:zend_fake_compare_objects", results = emptySet())
        assertCompare(type, "ext/ffi/ffi.c:zend_ffi_ctype_compare_objects")
        assertOperationsAbsent(ffi)
        assertOperationsAbsent(type)
    }

    // ========== unavailable configurations ==========

    // ext/dom/php_dom.c:1332-1350: the table of DOMXPath exists only when LIBXML_XPATH_ENABLED is defined; the other
    // configuration keeps a table with every slot unestablished as absent, and the class keeps both alternatives.
    @Test
    fun `a table of an unavailable configuration is kept as its own alternative`() {
        val tables = tablesOf("dom\\xpath")
        assertEquals(
            listOf(
                "ext/dom/php_dom.c:dom_xpath_object_handlers #defined(LIBXML_XPATH_ENABLED)",
                "ext/dom/php_dom.c:dom_xpath_object_handlers #!defined(LIBXML_XPATH_ENABLED)",
            ),
            tables.map { it.id },
        )
        assertCasts(tables.first(), STD_CAST, string = emptySet(), dispatch = METHOD_ONLY)
        assertOperationsAbsent(tables.first())
        val unavailable = tables.last()
        assertEquals(HandlerSlot.entries.toSet(), unavailable.facts.map { it.slot }.toSet())
        assertTrue(unavailable.facts.all { it.absent && it.request == null && it.targets.isEmpty() })
    }

    // ========== finality ==========

    // The registration flag of the class: Closure, Generator, FFI, FFI\CData, tidyNode and GMP are final; DateTime,
    // DateTimeImmutable, tidy, SimpleXMLElement and stdClass are not (final_classes). A final class stays final below
    // a user class only by the user declaration (finality_inherited), so no flag is inherited here.
    @Test
    fun `final native classes are final and open ones are not`() {
        val final = listOf("closure", "generator", "ffi\\cdata", "ffi", "ffi\\ctype", "gmp", "tidynode", "bcmath\\number")
        val open = listOf("datetimeimmutable", "datetime", "tidy", "simplexmlelement", "stdclass", "exception")
        for (name in final) assertEquals(true, signatureOf(name).isFinal, name)
        for (name in open) assertEquals(false, signatureOf(name).isFinal, name)
    }

    // ========== helpers ==========

    private fun signatureOf(name: String) =
        assertNotNull(assertNotNull(PhpStubs.clazz(name), name).classSignature, name)

    // A slot of a table is wholly absent (one fact) or answers every request of the slot, once each.
    private fun assertSlotComplete(table: HandlerTable, slot: HandlerSlot, requests: Set<HandlerRequest?>) {
        val facts = table.facts.filter { it.slot == slot }
        if (facts.singleOrNull()?.absent == true) return
        assertTrue(facts.none { it.absent }, "${table.id} $slot")
        assertEquals(requests.size, facts.size, "${table.id} $slot")
        assertEquals(requests, facts.map { it.request }.toSet(), "${table.id} $slot")
    }

    private fun tablesOf(name: String): List<HandlerTable> = signatureOf(name).handlers

    private fun singleTable(name: String): HandlerTable = tablesOf(name).single()

    private fun HandlerTable.target(slot: HandlerSlot, request: HandlerRequest?) =
        assertNotNull(facts.singleOrNull { it.slot == slot && it.request == request }, "$id $slot $request").targets.single()

    private fun assertCastTarget(
        table: HandlerTable,
        request: HandlerRequest,
        symbol: String,
        results: Set<ReturnKind>,
        dispatch: StringDispatch?,
    ) {
        val target = table.target(HandlerSlot.CAST, request)
        assertEquals(symbol, target.symbol, "${table.id} $request")
        assertEquals(results, target.results, "${table.id} $request")
        assertEquals(dispatch, target.stringDispatch, "${table.id} $request")
    }

    // Every cast of a table is served by [symbol]: the string with [string] and [dispatch], the boolean with [bool],
    // the numeric targets with [numbers], and the array and resource targets with [others].
    private fun assertCasts(
        table: HandlerTable,
        symbol: String,
        string: Set<ReturnKind>,
        dispatch: StringDispatch,
        numbers: Set<ReturnKind> = emptySet(),
        bool: Set<ReturnKind> = setOf(BOOL),
        others: Set<ReturnKind> = emptySet(),
    ) {
        assertCastTarget(table, IS_STRING, symbol, string, dispatch)
        assertCastTarget(table, _IS_BOOL, symbol, bool, null)
        for (request in listOf(IS_LONG, IS_DOUBLE, _IS_NUMBER)) assertCastTarget(table, request, symbol, numbers, null)
        for (request in listOf(IS_ARRAY, IS_RESOURCE)) assertCastTarget(table, request, symbol, others, null)
    }

    private fun assertCompare(table: HandlerTable, symbol: String, results: Set<ReturnKind> = setOf(NUM)) {
        val target = table.target(HandlerSlot.COMPARE, null)
        assertEquals(symbol, target.symbol, table.id)
        assertEquals(results, target.results, table.id)
        assertNull(target.stringDispatch, table.id)
    }

    // The operation slot is NULL: one whole-slot absence and no other operation fact.
    private fun assertOperationsAbsent(table: HandlerTable) {
        val operations = table.facts.filter { it.slot == HandlerSlot.OPERATION }
        val whole = operations.single()
        assertTrue(whole.absent && whole.request == null && whole.targets.isEmpty(), table.id)
    }

    // The opcodes in [producing] answer an object (any), except [numberOrObject], which may answer a number too; every
    // other opcode is served by [symbol] and fails (no normal result).
    private fun assertOperations(
        table: HandlerTable,
        symbol: String,
        producing: Set<String>,
        numberOrObject: Set<String> = emptySet(),
    ) {
        val operations = table.facts.filter { it.slot == HandlerSlot.OPERATION }
        assertEquals(HandlerRequest.entries.count { it.slot == HandlerSlot.OPERATION }, operations.size, table.id)
        for (fact in operations) {
            assertFalse(fact.absent, table.id)
            val target = fact.targets.single()
            val name = checkNotNull(fact.request).name
            val expected = when (name) {
                in numberOrObject -> setOf(NUM, ANY)
                in producing -> setOf(ANY)
                else -> emptySet()
            }
            assertEquals(symbol, target.symbol, "${table.id} $name")
            assertEquals(expected, target.results, "${table.id} $name")
        }
    }

    private companion object {
        const val STD_CAST = "Zend/zend_object_handlers.c:zend_std_cast_object_tostring"
        val SOURCE_SYMBOL = Regex("""[\w/+.-]+\.(c|h|cpp):\w+.*""")

        // Two PDO driver pseudo-classes of the generated documents and the five classes of PECL extensions: php-src
        // registers none of them, so they keep only the classifier.
        val PSEUDO = listOf("pdo_pgsql_ext", "pdo_sqlite_ext")
        val EXTERNAL = listOf("redis", "memcached", "imagick", "imagickdraw", "imagickpixel")

        // The generated documents and their class and enum entries, as the stub inventory lists them: one document per
        // line group, the subjects in declaration order.
        const val MANIFEST = """
        com_dotnet.yaml:
          com com_exception com_safearray_proxy compersisthelper dotnet variant
        core.yaml:
          exception error typeerror valueerror argumentcounterror arithmeticerror divisionbyzeroerror
          parseerror compileerror stdclass closure generator fiber weakreference weakmap
          allowdynamicproperties attribute closedgeneratorexception delayedtargetvalidation deprecated
          errorexception fibererror internaliterator nodiscard override requestparsebodyexception
          returntypewillchange sensitiveparameter sensitiveparametervalue unhandledmatcherror
        crypto/bcmath.yaml:
          bcmath\number
        crypto/gmp.yaml:
          gmp
        crypto/hash.yaml:
          hashcontext
        crypto/openssl.yaml:
          opensslasymmetrickey opensslcertificate opensslcertificatesigningrequest
        database/dba.yaml:
          dba\connection
        database/mysqli.yaml:
          mysqli_sql_exception mysqli_warning mysqli mysqli_result mysqli_stmt mysqli_driver
        database/odbc.yaml:
          odbc\connection odbc\result
        database/pgsql.yaml:
          pgsql\connection pgsql\lob pgsql\result
        dom.yaml:
          dom\adjacentposition dom\attr dom\cdatasection dom\characterdata dom\comment dom\document
          dom\documentfragment dom\documenttype dom\dtdnamednodemap dom\element dom\entity
          dom\entityreference dom\htmlcollection dom\htmldocument dom\htmlelement dom\implementation
          dom\namednodemap dom\namespaceinfo dom\node dom\nodelist dom\notation
          dom\processinginstruction dom\text dom\tokenlist dom\xmldocument dom\xpath domcdatasection
          domcharacterdata domdocumentfragment domdocumenttype domentity domentityreference
          domexception domimplementation domnamednodemap domnamespacenode domnotation
          domprocessinginstruction domxpath domnode domdocument domelement domnodelist domattr domtext
          domcomment
        enchant.yaml:
          enchantbroker enchantdictionary
        ffi.yaml:
          ffi ffi\cdata ffi\ctype ffi\exception ffi\parserexception
        file/fileinfo.yaml:
          finfo
        file/filter.yaml:
          filter\filterexception filter\filterfailedexception
        file/zip.yaml:
          ziparchive
        file/zlib.yaml:
          deflatecontext inflatecontext
        image/gd.yaml:
          gdfont gdimage
        misc/date.yaml:
          dateerror dateexception dateinvalidoperationexception dateinvalidtimezoneexception
          datemalformedintervalstringexception datemalformedperiodstringexception
          datemalformedstringexception dateobjecterror daterangeerror datetime datetimeimmutable
          datetimezone dateinterval dateperiod
        network/curl.yaml:
          curlfile curlsharepersistenthandle curlstringfile curlhandle curlmultihandle curlsharehandle
        network/ftp.yaml:
          ftp\connection
        network/ldap.yaml:
          ldap\connection ldap\result ldap\resultentry
        network/session.yaml:
          sessionhandler
        network/sockets.yaml:
          addressinfo socket
        pdo.yaml:
          pdorow pdo pdostatement pdoexception
        pdo_dblib.yaml:
          pdo\dblib
        pdo_firebird.yaml:
          pdo\firebird
        pdo_mysql.yaml:
          pdo\mysql
        pdo_odbc.yaml:
          pdo\odbc
        pdo_pgsql.yaml:
          pdo\pgsql pdo_pgsql_ext
        pdo_sqlite.yaml:
          pdo\sqlite pdo_sqlite_ext
        phar.yaml:
          phar phardata pharexception pharfileinfo
        random.yaml:
          random\brokenrandomengineerror random\engine\mt19937 random\engine\pcgoneseq128xslrr64
          random\engine\secure random\engine\xoshiro256starstar random\intervalboundary
          random\randomerror random\randomexception random\randomizer
        reflection.yaml:
          propertyhooktype reflection reflectionattribute reflectionclassconstant reflectionconstant
          reflectionenum reflectionenumbackedcase reflectionenumunitcase reflectionexception
          reflectionextension reflectionfiber reflectionfunctionabstract reflectiongenerator
          reflectionobject reflectionreference reflectionzendextension reflectionclass
          reflectionmethod reflectionfunction reflectionproperty reflectionparameter reflectiontype
          reflectionnamedtype reflectionuniontype reflectionintersectiontype
        shmop.yaml:
          shmop
        snmp.yaml:
          snmp snmpexception
        soap.yaml:
          soap\sdl soap\url soapheader soapparam soapvar soapclient soapserver soapfault
        sodium.yaml:
          sodiumexception
        sqlite3.yaml:
          sqlite3exception sqlite3 sqlite3stmt sqlite3result
        standard/standard_8.yaml:
          __php_incomplete_class assertionerror directory php_user_filter roundingmode streambucket
        system/pcntl.yaml:
          pcntl\qosclass
        system/spl.yaml:
          appenditerator cachingiterator callbackfilteriterator emptyiterator filesystemiterator
          filteriterator globiterator infiniteiterator iteratoriterator limititerator multipleiterator
          norewinditerator parentiterator recursivearrayiterator recursivecachingiterator
          recursivecallbackfilteriterator recursivefilteriterator recursiveiteratoriterator
          recursiveregexiterator recursivetreeiterator regexiterator spldoublylinkedlist splmaxheap
          splminheap spltempfileobject runtimeexception logicexception invalidargumentexception
          outofrangeexception outofboundsexception overflowexception underflowexception
          unexpectedvalueexception badmethodcallexception badfunctioncallexception domainexception
          lengthexception rangeexception arrayobject arrayiterator splfileinfo splfileobject
          splfixedarray splstack splqueue splheap splpriorityqueue splobjectstorage directoryiterator
          recursivedirectoryiterator
        system/sysvmsg.yaml:
          sysvmessagequeue
        system/sysvsem.yaml:
          sysvsemaphore
        system/sysvshm.yaml:
          sysvsharedmemory
        text/intl.yaml:
          intlbreakiterator intlchar intlcodepointbreakiterator intldatepatterngenerator intlexception
          intlgregoriancalendar intliterator intllistformatter intlpartsiterator
          intlrulebasedbreakiterator uconverter intldateformatter numberformatter collator
          messageformatter locale normalizer resourcebundle transliterator spoofchecker intlcalendar
          intltimezone
        text/json.yaml:
          jsonexception
        tokenizer.yaml:
          phptoken
        uri.yaml:
          uri\invaliduriexception uri\rfc3986\uri uri\uricomparisonmode uri\urierror uri\uriexception
          uri\whatwg\invalidurlexception uri\whatwg\url uri\whatwg\urlvalidationerror
          uri\whatwg\urlvalidationerrortype
        xml/libxml.yaml:
          libxmlerror
        xml/simplexml.yaml:
          simplexmliterator simplexmlelement
        xml/tidy.yaml:
          tidy tidynode
        xml/xml.yaml:
          xmlparser
        xml/xmlwriter.yaml:
          xmlwriter
        xmlreader.yaml:
          xmlreader
        xsl.yaml:
          xsltprocessor
"""
    }

    private fun readManifest(): Map<String, List<String>> {
        val result = LinkedHashMap<String, MutableList<String>>()
        var document = ""
        for (line in MANIFEST.trimIndent().lines().filter { it.isNotBlank() }) {
            if (!line.startsWith(" ")) {
                document = line.removeSuffix(":")
                result[document] = mutableListOf()
            } else {
                result.getValue(document) += line.trim().split(" ")
            }
        }
        return result
    }
}
