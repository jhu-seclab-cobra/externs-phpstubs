[Owning design](design.md).

# Resource coverage gaps

- Which producer or declaration error explains these constant differences? `E_ALL`, `T_ABSTRACT`, `T_STRING`, `T_VARIABLE`, `T_LNUMBER`, `T_DNUMBER`,
  `FILTER_VALIDATE_MAC` and `OPENSSL_ALGO_MD5` are declared with values that
  differ from PHP 8.5.12 (`E_ALL` 32767 against 30719, `FILTER_VALIDATE_MAC`
  281 against 276, `OPENSSL_ALGO_MD5` 4 against 2); the cause (PHP version or
  declaration error) is not established.
- How should the constant producer cover the missing extension declarations? The models declare 242 of the 3025 constants PHP 8.5.12 defines (extension constants such as `FILEINFO_*`,
  `LIBXML_*` and `SOAP_*` among the missing ones; `CURLOPT_URL`, `SEEK_SET` and `LOCK_EX` are declared). A call
  with an undeclared constant as an argument is reported by no sink, so `new finfo(FILEINFO_NONE, $_GET['m'])` and
  `new SimpleXMLElement($_GET['u'], LIBXML_NOENT, true)` report nothing while the same calls with the literal flag
  report their constructor sink.
- Which remaining URL-reading builtins require a sink Fact? Builtins that send a request for the URL in an argument on PHP 8.5.12 and carry no `ssrf` in `sinks.yaml`, so a
  program passing a request value to them reports nothing: `Dom\XMLDocument::createFromFile`,
  `Dom\Document::schemaValidate` and `Dom\Document::relaxNgValidate` (the PHP manual documents no method of
  `Dom\Document` or `Dom\XMLDocument`, so the second source is missing). Not run, because the extension
  is absent or the call needs a service:
  `yaml_parse_file`, `yaml_parse_url`, `ldap_connect`, the `http_*` and `swoole` request functions and the other
  builtins of `models/` whose `filename`, `uri` or `url` parameter reads or fetches.
- Should declarations absent from the target PHP release be removed? `PHP_FLOAT_INF`, `PHP_FLOAT_NAN`, `ARRAY_UNIQUE_REGULAR` and the
  `PDO_FETCH_*` constants are declared, but PHP 8.5.12 defines none of them.
- How can constant regeneration preserve the manual declaration exclusion? The three php-src tools write no constant entries, and `tools/convert_stubs.py`, named by `models/provenance.yaml`, is absent. The producer has no available exclusion mechanism for the subjects declared in `manual/core.yaml`; duplicate detection and `ManualDeclarationsTest` are the checks that detect overlap.
