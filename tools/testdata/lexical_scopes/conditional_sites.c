typedef int (*review_callback)(void);
typedef int name;
struct review_named_cell { int name; };
static int review_five(void) { return 5; }
static int review_thirteen(void) { return 13; }

int review_conditional_type_words(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  name temporary = 0;
  struct review_named_cell cell = {.name = 0};
  return value + cell.name - temporary;
 }
}

int review_conditional_subsequent(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  value += 2;
  { int value = 99; }
  return value;
 }
}

int review_conditional_alias(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  int *saved = &value;
  *saved += 2;
  return value;
 }
}

int review_conditional_parameter(int value) {
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  return value;
 }
}

int review_conditional_array(void) {
 int initial = 13, *value = &initial;
 {
#if defined(REVIEW_CHOICE)
  int value[] = {5};
#endif
  return value[0];
 }
}

int review_conditional_sizeof(void) {
 char value = 13;
 {
#if defined(REVIEW_CHOICE)
  long value = 5;
#endif
  return sizeof(value);
 }
}

int review_conditional_global_call(void) {
#if defined(REVIEW_CHOICE)
 review_callback review_thirteen = review_five;
#endif
 return review_thirteen();
}

int review_conditional_expression(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  int total = ({ int saved = value; { int value = 99; } saved; });
  return total + value;
 }
}

int review_conditional_correlated(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  return value - value;
 }
}

int review_conditional_branch_write(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#else
  value = 7;
#endif
  return value;
 }
}

int review_conditional_loop(void) {
 int value = 13, count = 0;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  while (count++ < 2) {
   int saved = value;
   { int value = 99; }
   if (saved != value) { return 0; }
  }
  return value;
 }
}

int review_conditional_nested(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  {
#if defined(REVIEW_SECOND)
   int value = 7;
#endif
   return value;
  }
 }
}

int review_conditional_elif(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#elif defined(REVIEW_SECOND)
  int value = 7;
#else
  ;
#endif
  return value;
 }
}

static int review_cast_conditional_retry(zend_object *object, zval *out, int type) {
 int value = 13, count = 0;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  int total = ({ int saved = value; review_identity(saved + count++); });
  { int value = 99; }
  if (value == 13 && total == 13 && count == 1) { ZVAL_LONG(out, 1); }
  else if (value == 5 && total == 5 && count == 1) { ZVAL_STR(out, NULL); }
  else { Z_TYPE_INFO_P(out) = IS_TRUE; }
 }
 return SUCCESS;
}

int review_conditional_unused(void) {
#if defined(REVIEW_UNUSED_0)
 int local_0 = 0;
 (void)local_0;
#endif
#if defined(REVIEW_UNUSED_1)
 int local_1 = 1;
 (void)local_1;
#endif
#if defined(REVIEW_UNUSED_2)
 int local_2 = 2;
 (void)local_2;
#endif
#if defined(REVIEW_UNUSED_3)
 int local_3 = 3;
 (void)local_3;
#endif
#if defined(REVIEW_UNUSED_4)
 int local_4 = 4;
 (void)local_4;
#endif
#if defined(REVIEW_UNUSED_5)
 int local_5 = 5;
 (void)local_5;
#endif
#if defined(REVIEW_UNUSED_6)
 int local_6 = 6;
 (void)local_6;
#endif
#if defined(REVIEW_UNUSED_7)
 int local_7 = 7;
 (void)local_7;
#endif
#if defined(REVIEW_UNUSED_8)
 int local_8 = 8;
 (void)local_8;
#endif
#if defined(REVIEW_UNUSED_9)
 int local_9 = 9;
 (void)local_9;
#endif
#if defined(REVIEW_UNUSED_10)
 int local_10 = 10;
 (void)local_10;
#endif
#if defined(REVIEW_UNUSED_11)
 int local_11 = 11;
 (void)local_11;
#endif
#if defined(REVIEW_UNUSED_12)
 int local_12 = 12;
 (void)local_12;
#endif
#if defined(REVIEW_UNUSED_13)
 int local_13 = 13;
 (void)local_13;
#endif
#if defined(REVIEW_UNUSED_14)
 int local_14 = 14;
 (void)local_14;
#endif
 return 13;
}
