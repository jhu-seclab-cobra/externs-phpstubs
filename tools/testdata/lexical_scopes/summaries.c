static int scope_amount(int value) { return value; }
static void scope_fill(zval *out, int type) { Z_TYPE_INFO_P(out) = type; }

static int scope_cast_checkpoint(zend_object *object, zval *out, int type) {
 int value = 7, count = 0;
 {
  int value = ({ int saved = count++; saved + scope_amount(count++); });
  if (value != 1) { ZVAL_STR(out, NULL); return SUCCESS; }
 }
 if (value == 7 && count == 2) { ZVAL_LONG(out, 1); }
 else { ZVAL_STR(out, NULL); }
 return SUCCESS;
}

static int scope_cast_aliases(zend_object *object, zval *out, int type) {
 zval value;
 scope_fill(&value, IS_LONG);
 zval *saved = &value;
 {
  zval value;
  scope_fill(&value, IS_STRING);
  if (Z_TYPE_INFO_P(saved) != IS_LONG) { ZVAL_STR(out, NULL); return SUCCESS; }
 }
 Z_TYPE_INFO_P(out) = Z_TYPE_INFO(value);
 return SUCCESS;
}

static int scope_cast_cached(zend_object *object, zval *out, int type) {
 zval value;
 scope_fill(&value, IS_LONG);
 { zval value; scope_fill(&value, IS_LONG); ZVAL_STR(&value, NULL); }
 { zval value; scope_fill(&value, IS_LONG); ZVAL_STR(&value, NULL); }
 Z_TYPE_INFO_P(out) = Z_TYPE_INFO(value);
 return SUCCESS;
}

static int scope_cast_loop(zend_object *object, zval *out, int type) {
 int value = 7;
 for (int index = 0; index < 2; ++index) {
  int value = scope_amount(index);
 }
 if (value == 7) { ZVAL_LONG(out, 1); } else { ZVAL_STR(out, NULL); }
 return SUCCESS;
}

static void scope_recursive(zval *out, int count) {
 int value = count;
 if (count) {
  { int value = count + 1; scope_recursive(out, count - 1); }
  if (value != count) { ZVAL_STR(out, NULL); }
 } else { ZVAL_LONG(out, 1); }
}

static int scope_cast_recursive(zend_object *object, zval *out, int type) {
 scope_recursive(out, 3);
 return SUCCESS;
}
