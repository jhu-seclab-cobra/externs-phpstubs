struct review_cell { int value; };

int review_nested(void) {
 int value = 3, total = 0;
 { int value = 5;
  { int value = 7; { int value = 11; total += value; } total += value; }
  total += value;
 }
 return total + value;
}

int review_parameter(int value) {
 { int value = 99; value++; }
 return value;
}

int review_for_init(void) {
 int value = 13, total = 0;
 for (int value = 0; value < 3; ++value) { total += value; }
 return value;
}

int review_switch(void) {
 int value = 13, total = 0;
 switch (2) {
 case 1: total = 100; break;
 case 2: { int value = 5; { int value = 7; total = value; } total += value; }
 case 3: total += value; break;
 default: total = 200;
 }
 return total + value;
}

int review_case_entry(void) {
 int value = 13;
 switch (2) {
 case 1: ; int value = 5;
 case 2: return value;
 }
 return value;
}

int review_goto(void) {
 int value = 13;
 { int value = 5; { int value = 7; goto done; } }
done:
 return value;
}

int review_break(void) {
 int value = 13;
 while (1) { int value = 5; { int value = 7; break; } }
 return value;
}

int review_continue(void) {
 int value = 13, total = 0;
 for (int value = 0; value < 3; ++value) {
  { int value = 9; total++; continue; }
 }
 return value;
}

int review_self_initializer(void) {
 int value = 13;
 { int value = value; return value; }
}

int review_outer_initializer(void) {
 int value = 13, *outer = &value, total = 0;
 { int value = *outer + 2; total = value; }
 return total + value;
}

int review_declarators(void) {
 int value = 13, total = 0;
 { int before = value, value = before + 2, after = value + 1; total = after; }
 return total + value;
}

int review_expression(void) {
 int value = 13;
 int total = ({ int value = 5; int nested = ({ int value = 7; value; }); nested + value; });
 return total + value;
}

int review_alias_copy(void) {
 struct review_cell value = {.value = 13}, copy;
 struct review_cell *outer = &value;
 { struct review_cell value = {.value = 5}; copy = value; outer->value += value.value; }
 return value.value + copy.value;
}

int review_conditional_first(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#else
  ;
#endif
  return value;
 }
}

int review_conditional_last(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  ;
#else
  int value = 5;
#endif
  return value;
 }
}

int review_conditional_absent(void) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#endif
  return value;
 }
}

static int review_identity(int value) { return value; }

static int review_cast_retry(zend_object *object, zval *out, int type) {
 int value = 13, count = 0, total = 0;
 count++;
 { int value = 5;
  { int value = 7; total = review_identity(value + count++); total += value; }
  total += value;
 }
 if (value == 13 && count == 2 && total == 20) { ZVAL_LONG(out, total); }
 else { ZVAL_STR(out, NULL); }
 return SUCCESS;
}

static int review_cast_inline_retry(zend_object *object, zval *out, int type) {
 int value = 13, count = 0;
 int total = ({ int value = 5; int saved = count++; review_identity(value + count++) + saved; });
 if (value == 13 && count == 2 && total == 6) { ZVAL_LONG(out, total); }
 else { ZVAL_STR(out, NULL); }
 return SUCCESS;
}

static int review_cast_conditional(zend_object *object, zval *out, int type) {
 int value = 13;
 {
#if defined(REVIEW_CHOICE)
  int value = 5;
#else
  ;
#endif
  if (value == 13) { ZVAL_LONG(out, 1); }
  else { ZVAL_STR(out, NULL); }
 }
 return SUCCESS;
}
