PHP_FUNCTION(check_shadowed_collection) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 HashTable *local = NULL;
 {
  HashTable *local = named;
 }
 zend_call_known_function(target, object, scope, result, argc, args, local);
}

PHP_FUNCTION(check_shadowed_fci) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 zend_fcall_info fci;
 fci.named_params = NULL;
 {
  zend_fcall_info fci;
  fci.named_params = named;
 }
 zend_call_function(&fci, &fcc);
}

static void shadow_parameter(HashTable *local, HashTable *named) {
 {
  HashTable *local = named;
 }
 zend_call_known_function(target, object, scope, result, argc, args, local);
}
PHP_FUNCTION(check_shadowed_parameter) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 shadow_parameter(NULL, named);
}
PHP_FUNCTION(check_shadowed_for) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 HashTable *local = NULL;
 for (HashTable *local = named; 1;) { break; }
 zend_call_known_function(target, object, scope, result, argc, args, local);
}
PHP_FUNCTION(check_shadowed_expression) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 HashTable *local = NULL;
 ({ HashTable *local = named; 0; });
 zend_call_known_function(target, object, scope, result, argc, args, local);
}
PHP_FUNCTION(check_shadowed_ancestor) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 HashTable *local = NULL;
 { { HashTable *local = named; } }
 zend_call_known_function(target, object, scope, result, argc, args, local);
}
PHP_FUNCTION(check_shadowed_outer_reference) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 HashTable *saved = named;
 named = NULL;
 { HashTable *named = saved; }
 zend_call_known_function(target, object, scope, result, argc, args, named);
}
PHP_FUNCTION(check_sibling_scopes) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 int sum = 0;
 { int temporary = 1; sum += temporary; }
 { int temporary = 2; sum += temporary; }
 zend_call_known_function(target, object, scope, result, argc, args, named);
}
PHP_FUNCTION(check_local_forward) {
 ZEND_PARSE_PARAMETERS_START(0, -1)
  Z_PARAM_VARIADIC_WITH_NAMED(args, argc, named)
 ZEND_PARSE_PARAMETERS_END();
 {
  HashTable *local = named;
  zend_call_known_function(target, object, scope, result, argc, args, local);
 }
}
