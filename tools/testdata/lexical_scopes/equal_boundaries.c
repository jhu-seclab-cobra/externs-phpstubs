int check3_values(void) {
#if defined(REVIEW_CHOICE)
 int value = 11;
#else
 int value = 19;
#endif
 return value;
}

int check3_elif_else(void) {
#if defined(REVIEW_CHOICE)
 int value = 11;
#elif defined(REVIEW_SECOND)
 int value = 19;
#else
 int value = 23;
#endif
 return value;
}

int check3_elif_implicit(void) {
 int value = 31;
 {
#if defined(REVIEW_CHOICE)
  int value = 11;
#elif defined(REVIEW_SECOND)
  int value = 19;
#endif
  return value;
 }
}

int check3_nested(void) {
 int value = 31;
 {
#if defined(REVIEW_CHOICE)
#if defined(REVIEW_SECOND)
  int value = 11;
#else
  int value = 19;
#endif
#else
  ;
#endif
  return value;
 }
}

int check3_inline(void) {
 return ({
#if defined(REVIEW_CHOICE)
  int value = 11;
#else
  int value = 19;
#endif
  value;
 });
}

int check3_correlation(void) {
#if defined(REVIEW_CHOICE)
 int value = 11;
#else
 int value = 19;
#endif
 return value - value;
}

int check3_inline_correlation(void) {
 return ({
#if defined(REVIEW_CHOICE)
  int value = 11;
#else
  int value = 19;
#endif
  value - value;
 });
}

static int check3_cast_handler(zend_object *object, zval *out, int type) {
#if defined(REVIEW_CHOICE)
 int first = 11, second = 19;
#else
 int first = 19, second = 11;
#endif
 if (first + second == 30) { ZVAL_LONG(out, 1); }
 else { ZVAL_STR(out, NULL); }
 return SUCCESS;
}

static int check3_cast_loop(zend_object *object, zval *out, int type) {
 int value = 31;
 for (int iteration = 0; iteration < 2; ++iteration) {
#if defined(REVIEW_CHOICE)
  int value = 11;
#else
  int value = 19;
#endif
  int count = 0;
  int saved = review_identity(value + count++);
  if (count != 1 || saved != value) { ZVAL_STR(out, NULL); return SUCCESS; }
 }
 if (value == 31) { ZVAL_LONG(out, 1); } else { ZVAL_STR(out, NULL); }
 return SUCCESS;
}
