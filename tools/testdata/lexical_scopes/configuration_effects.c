int check3_dependent_reads(void) {
#if defined(REVIEW_CHOICE)
 int input = 11, value = input;
#else
 int input = 19, value = input;
#endif
 return value - value;
}

int check3_later_writes(void) {
#if defined(REVIEW_CHOICE)
 int value = 0;
 value = 11;
#else
 int value = 0;
 value = 19;
#endif
 return value - value;
}

int check3_alias_values(void) {
#if defined(REVIEW_CHOICE)
 int value = 11, *saved = &value;
#else
 int value = 19, *saved = &value;
#endif
 return *saved - *saved;
}

int check3_constant_expressions(void) {
#if defined(REVIEW_CHOICE)
 int first = 1 + 2, second = 4 * 5;
#else
 int first = 1 + 2, second = 4 * 5;
#endif
 return first + second;
}
