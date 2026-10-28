int check2_inline_same_binding(void) {
 return ({
#if defined(REVIEW_CONTROL_0)
 int local_0 = 0;
#else
 int local_0 = 0;
#endif
 (void)local_0;
#if defined(REVIEW_CONTROL_1)
 int local_1 = 0;
#else
 int local_1 = 0;
#endif
 (void)local_1;
#if defined(REVIEW_CONTROL_2)
 int local_2 = 0;
#else
 int local_2 = 0;
#endif
 (void)local_2;
#if defined(REVIEW_CONTROL_3)
 int local_3 = 0;
#else
 int local_3 = 0;
#endif
 (void)local_3;
#if defined(REVIEW_CONTROL_4)
 int local_4 = 0;
#else
 int local_4 = 0;
#endif
 (void)local_4;
#if defined(REVIEW_CONTROL_5)
 int local_5 = 0;
#else
 int local_5 = 0;
#endif
 (void)local_5;
#if defined(REVIEW_CONTROL_6)
 int local_6 = 0;
#else
 int local_6 = 0;
#endif
 (void)local_6;
 13;
 });
}

static int check2_cast_inline_same_binding(zend_object *object, zval *out, int type) {
 int result = check2_inline_same_binding();
 if (result == 13) { ZVAL_LONG(out, result); } else { ZVAL_STR(out, NULL); }
 return SUCCESS;
}

int check2_same_binding_values(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#else
  int value = 7;
#endif
  return value;
 }
}

int check2_same_binding_elif(void) {
#if defined(REVIEW_CHOICE)
 int value = 5;
#elif defined(REVIEW_SECOND)
 int value = 7;
#else
 int value = 11;
#endif
 return value;
}

int check2_optional_binding_elif(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#elif defined(REVIEW_SECOND)
  int value = 5;
#endif
  return value;
 }
}
