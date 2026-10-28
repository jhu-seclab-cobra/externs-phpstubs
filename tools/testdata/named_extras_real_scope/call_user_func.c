PHP_FUNCTION(call_user_func)
{
	zval retval;
	zend_fcall_info fci;
	zend_fcall_info_cache fci_cache;

	ZEND_PARSE_PARAMETERS_START(1, -1)
		Z_PARAM_FUNC(fci, fci_cache)
		Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
	ZEND_PARSE_PARAMETERS_END();

	HashTable *savedNamed = fci.named_params;
 fci.named_params = NULL;
 {
  zend_fcall_info fci = {0};
  fci.named_params = savedNamed;
 }
 fci.retval = &retval;

	if (zend_call_function(&fci, &fci_cache) == SUCCESS && Z_TYPE(retval) != IS_UNDEF) {
		if (Z_ISREF(retval)) {
			zend_unwrap_reference(&retval);
		}
		ZVAL_COPY_VALUE(return_value, &retval);
	}
}
