/* Engine support the handlers call, and the registration functions of the classes of handlers.c in the shape the
   php-src stub generator writes them. */
#define ZEND_ACC_INTERFACE 1
extern int VariantCopy(VARIANT *dst, VARIANT *src);
extern int VariantChangeType(VARIANT *dst, VARIANT *src, int flags, int type);
ZEND_API int zend_std_cast_object_tostring(zend_object *readobj, zval *writeobj, int type)
{
	zend_class_entry *ce = readobj->ce;
	if (type == IS_STRING && ce->__tostring) {
		zend_call_known_instance_method_with_0_params(ce->__tostring, readobj, writeobj);
		return SUCCESS;
	}
	return FAILURE;
}
ZEND_API bool instanceof_function_slow(const zend_class_entry *instance_ce, const zend_class_entry *ce)
{
	if (ce->ce_flags & ZEND_ACC_INTERFACE) {
		return 0;
	}
	while (1) {
		instance_ce = instance_ce->parent;
		if (instance_ce == ce) {
			return 1;
		}
		if (instance_ce == NULL) {
			return 0;
		}
	}
}
static bool instanceof_function(const zend_class_entry *instance_ce, const zend_class_entry *ce)
{
	return instance_ce == ce || instanceof_function_slow(instance_ce, ce);
}
#define ZVAL_OBJ(z, o) do { zval *__z = (z); Z_OBJ_P(__z) = (o); Z_TYPE_INFO_P(__z) = IS_OBJECT; } while (0)
#define SUCCEEDED(hr) ((hr) >= 0)
#define S_OK 0
#define VT_EMPTY 0
#define VT_BSTR 8
#define VT_I8 20
typedef struct _variant { zend_long vt; zend_long value; } VARIANT;
#define V_VT(v) ((v)->vt)
#define ZEND_UNCOMPARABLE 1
static zend_class_entry *register_class_Rurl(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rurl", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rsdl(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rsdl", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rbundle(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rbundle", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rpos(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rpos", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rdes(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rdes", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rzero(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rzero", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rbase(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rbase", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rsnap(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rsnap", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rchild(zend_class_entry *class_entry_Rbase)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rchild", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, class_entry_Rbase, 0);
	return class_entry;
}
static zend_class_entry *register_class_Ralias(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Ralias", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rcond(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rcond", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rtidya(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rtidya", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rtidyb(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rtidyb", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rlink(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rlink", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rlinkchild(zend_class_entry *class_entry_Rlink)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rlinkchild", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, class_entry_Rlink, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rstmt(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rstmt", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rother(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rother", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rgmp(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rgmp", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, ZEND_ACC_FINAL);
	return class_entry;
}
static zend_class_entry *register_class_Rcdata(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rcdata", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, ZEND_ACC_FINAL|ZEND_ACC_NO_DYNAMIC_PROPERTIES);
	return class_entry;
}
static zend_class_entry *register_class_Rcom(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rcom", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rconv(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rconv", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rexc(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rexc", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rrec(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rrec", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Rfinal(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rfinal", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, ZEND_ACC_FINAL);
	return class_entry;
}
static zend_class_entry *register_class_Rface(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Rface", NULL);
	class_entry = zend_register_internal_interface(&ce);
	return class_entry;
}
static zend_class_entry *register_class_Renum(zend_class_entry *class_entry_Rface)
{
	zend_class_entry *class_entry = zend_register_internal_enum("Renum", IS_UNDEF, NULL);
	return class_entry;
}
