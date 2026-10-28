struct scope_cell { int value; };

int scope_parameter(int value) {
 { int value = 9; }
 return value;
}

int scope_ancestors(void) {
 int value = 1, total = 0;
 { int value = 2; { int value = 3; total += value; } total += value; }
 return total + value;
}

int scope_source_order(void) {
 int value = 5, total = 0;
 { total = value; int value = 7; total += value; }
 return total + value;
}

int scope_declarators(void) {
 int value = 5, total = 0;
 { int first = value, value = 3, last = first + value; total = last; }
 return total + value;
}

int scope_self_initializer(void) {
 int value = 5;
 { int value = value; return value; }
}

int scope_for_init(void) {
 int value = 7;
 for (int value = 0; value < 2; ++value) { }
 return value;
}

int scope_for_body(void) {
 int index = 7;
 for (int index = 0; index < 2; ++index) { int index = 10; }
 return index;
}

int scope_statement_expression(void) {
 int value = 1;
 int result = ({ int value = 2; value; }) + value;
 return result + value;
}

int scope_nested_expression(void) {
 int value = 1;
 int result = ({ int value = 2; int inner = ({ int value = 3; value; }); inner + value; });
 return result + value;
}

int scope_break(void) {
 int value = 7;
 while (1) { int value = 2; break; }
 return value;
}

int scope_continue(void) {
 int value = 7;
 for (int index = 0; index < 2; ++index) { int value = 9; continue; }
 return value;
}

int scope_goto_out(void) {
 int value = 7;
 { int value = 2; goto done; }
done:
 return value;
}

int scope_goto_back(void) {
 int value = 3, count = 0;
again:
 if (count++ == 0) { int value = 9; goto again; }
 return value;
}

int scope_goto_into(void) {
 int value = 1;
 goto inner;
 { int value = 2;
inner:
  return value;
 }
}

int scope_return(void) {
 int value = 7;
 { int value = 2; return value; }
}

int scope_switch(void) {
 int value = 7, total = 0;
 switch (1) {
 case 1: { int value = 2; total = value; }
 case 2: total += value; break;
 }
 return total;
}

int scope_siblings(int flag) {
 int value = 7, total = 0;
 if (flag) { int value = 2; total = value; }
 else { int value = 3; total = value; }
 return total + value;
}

int scope_aliases(void) {
 int value = 3;
 int *outer = &value;
 { int value = 9; int *inner = &value; *outer += *inner; }
 return value;
}

int scope_struct_copy(void) {
 struct scope_cell value = {.value = 3};
 struct scope_cell copy = value;
 { struct scope_cell value = {.value = 9}; value.value++; }
 return copy.value + value.value;
}

int scope_memory_copy(void) {
 struct scope_cell value = {.value = 3}, copy = {.value = 0};
 { struct scope_cell value = {.value = 9}; memcpy(&copy, &value, sizeof(value)); }
 return copy.value + value.value;
}

int scope_array(void) {
 int value[2] = {1, 2};
 { int value = 9; }
 return value[0] + value[1];
}

int scope_sizeof(void) {
 int value = 1;
 { struct scope_cell value = {.value = 3}; }
 return sizeof(value);
}

int scope_expired_alias(void) {
 int *saved;
 { int value = 9; saved = &value; }
 return *saved;
}

int scope_configured_declarations(void) {
#if defined(SCOPE_CHOICE)
 int value = 2;
#else
 int value = 3;
#endif
 return value;
}

int scope_configured_references(void) {
 int value = 5, total = 0;
 {
#if defined(SCOPE_CHOICE)
  int value = 2;
  total = value;
#else
  total = value;
  int value = 3;
#endif
 }
 return total + value;
}
