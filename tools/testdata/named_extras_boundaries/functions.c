#define Z_PARAM_CONDITIONAL(dest) if (flag) { Z_PARAM_LONG(dest); }
PHP_FUNCTION(conditional_reception) {
 ZEND_PARSE_PARAMETERS_START(1, -1)
  Z_PARAM_CONDITIONAL(value)
  Z_PARAM_VARIADIC('*', args, argc)
 ZEND_PARSE_PARAMETERS_END();
}
static void clear_named(zend_fcall_info *info) { info->named_params = NULL; }
PHP_FUNCTION(clobbered_fci) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
 ZEND_PARSE_PARAMETERS_END();
 clear_named(&fci);
 zend_call_function(&fci, &fcc);
}
PHP_FUNCTION(early_success) {
 RETURN_TRUE;
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 zend_call_known_function(target, object, scope, result, argc, args, named);
}
PHP_FUNCTION(unreachable_forward) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 if (0) { zend_call_known_function(target, object, scope, result, argc, args, named); }
 RETURN_TRUE;
}
PHP_FUNCTION(zeroed_fci) {
 zend_fcall_info fci;
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
 ZEND_PARSE_PARAMETERS_END();
 memset(&fci, 0, sizeof(fci));
 zend_call_function(&fci, &fcc);
}
#define Z_PARAM_MUTATED(dest) do { Z_PARAM_PROLOGUE(0, 0); _i |= 1; } while (0)
PHP_FUNCTION(mutated_counter) {
 ZEND_PARSE_PARAMETERS_START(1, -1)
  Z_PARAM_MUTATED(value)
  Z_PARAM_VARIADIC('*', args, argc)
 ZEND_PARSE_PARAMETERS_END();
}
PHP_FUNCTION(unread_guard) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 if (unknown_guard()) { zend_call_known_function(target, object, scope, result, argc, args, named); }
}
static int false_guard(void) { return 0; }
PHP_FUNCTION(false_guarded) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 if (false_guard()) { zend_call_known_function(target, object, scope, result, argc, args, named); }
}
static void clear_alias(zend_fcall_info *info) {
 zend_fcall_info *alias = info;
 clear_named(alias);
}
PHP_FUNCTION(aliased_fci) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
 ZEND_PARSE_PARAMETERS_END();
 clear_alias(&fci);
 zend_call_function(&fci, &fcc);
}
static int read_count(zend_fcall_info *info) { return info->param_count; }
PHP_FUNCTION(preserved_fci) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
 ZEND_PARSE_PARAMETERS_END();
 read_count(&fci);
 zend_call_function(&fci, &fcc);
}
static void unused_callback(void) { zend_call_function(&fci, &fcc); }
static void keep_callback(void (*callback)(void)) { return; }
PHP_FUNCTION(unbound_callback) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
 ZEND_PARSE_PARAMETERS_END();
 keep_callback(unused_callback);
}

static void clear_collection(zend_fcall_info *info) { info->named_params->nNumUsed = 0; }
PHP_FUNCTION(mutated_collection) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
 ZEND_PARSE_PARAMETERS_END();
 clear_collection(&fci);
 zend_call_function(&fci, &fcc);
}
#define Z_PARAM_RECURSIVE(dest) Z_PARAM_RECURSIVE(dest)
PHP_FUNCTION(recursive_macro) {
 ZEND_PARSE_PARAMETERS_START(1, -1)
  Z_PARAM_RECURSIVE(value)
  Z_PARAM_VARIADIC('*', args, argc)
 ZEND_PARSE_PARAMETERS_END();
}

PHP_FUNCTION(unread_intervening_call) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 unknown_call();
 zend_call_known_function(target, object, scope, result, argc, args, named);
}

static void rebound_helper(INTERNAL_FUNCTION_PARAMETERS, int variadic) {
 variadic = 0;
 if (variadic) {
  ZEND_PARSE_PARAMETERS_START(0, -1)
   Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
  ZEND_PARSE_PARAMETERS_END();
  zend_call_known_function(target, object, scope, result, argc, args, named);
 }
}
PHP_FUNCTION(rebound_argument) { rebound_helper(INTERNAL_FUNCTION_PARAM_PASSTHRU, 1); }

static void relay_call(zend_fcall_info *info) { zend_call_function(info, &fcc); }
PHP_FUNCTION(unread_before_helper) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
 ZEND_PARSE_PARAMETERS_END();
 RETURN_UNREAD;
 relay_call(&fci);
}
PHP_FUNCTION(unread_inline_before_helper) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(fci.params, fci.param_count, fci.named_params)
 ZEND_PARSE_PARAMETERS_END();
 ({ RETURN_UNREAD; 0; });
 relay_call(&fci);
}
#define Z_PARAM_BRANCHES(dest) if (flag) { Z_PARAM_LONG(dest); } else { Z_PARAM_LONG(dest); }
PHP_FUNCTION(conditional_prologues) {
 ZEND_PARSE_PARAMETERS_START(1, -1)
  Z_PARAM_BRANCHES(value)
  Z_PARAM_VARIADIC('*', args, argc)
 ZEND_PARSE_PARAMETERS_END();
}

#define Z_PARAM_COUNTER_ALIAS(counter) counter ^= 1;
PHP_FUNCTION(counter_argument_write) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_COUNTER_ALIAS(_i)
  Z_PARAM_VARIADIC('*', args, argc)
 ZEND_PARSE_PARAMETERS_END();
}
