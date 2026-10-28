static int setjmp(void *environment) { return 1; }
PHP_FUNCTION(shadowed_jump) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 if (setjmp(&environment) == 0) {
  zend_call_known_function(target, object, scope, result, argc, args, named);
 }
}

static int zend_call_function(zend_fcall_info *info, zend_fcall_info_cache *cache) { return 0; }
PHP_FUNCTION(shadowed_target) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
 ZEND_PARSE_PARAMETERS_END();
 zend_call_function(&fci, &fcc);
}
