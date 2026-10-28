/* The handler write patterns of php-src, in the smallest form that keeps each one's shape. The comment above each
   block names the php-src code it follows. */
#include "handlers.h"

typedef struct _real_object {
	zend_long first;
	zend_long second;
	zend_object std;
} real_object;

typedef struct _real_cdata {
	void *ptr;
	zend_object std;
} real_cdata;

typedef struct _real_link {
	zend_long state;
	zend_object zo;
} real_link;

static zend_object_handlers url_handlers, sdl_handlers, bundle_handlers, zero_handlers, base_handlers, snap_handlers;
static zend_object_handlers alias_handlers, cond_handlers, tidy_doc_handlers, tidy_node_handlers;
static zend_object_handlers link_handlers, stmt_handlers, plain_link_handlers, gmp_handlers, com_handlers;
static zend_object_handlers conv_handlers, exc_handlers, rec_handlers;
static zend_object_handlers cdata_handlers, cdata_value_handlers, cdata_free_handlers;
zend_class_entry *link_ce;
zend_class_entry *stmt_ce;

static int cast_long(zend_object *readobj, zval *retval, int type)
{
	ZVAL_LONG(retval, 1);
	return SUCCESS;
}
static int cast_string(zend_object *readobj, zval *retval, int type)
{
	ZVAL_STR(retval, NULL);
	return SUCCESS;
}
static int cast_sdl(zend_object *readobj, zval *retval, int type)
{
	ZVAL_TRUE(retval);
	return SUCCESS;
}
static int compare_unordered(zval *o1, zval *o2)
{
	return ZEND_UNCOMPARABLE;
}
static int compare_throwing(zval *o1, zval *o2)
{
	zend_throw_error(NULL, "not comparable");
	return ZEND_UNCOMPARABLE;
}

/* ext/soap/soap.c: the cast handler of the second table is written to the first table. */
static void register_soap_like(void)
{
	zend_class_entry *url_ce = register_class_Rurl();
	url_ce->default_object_handlers = &url_handlers;
	memcpy(&url_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	url_handlers.cast_object = cast_long;
	url_handlers.compare = compare_unordered;
	zend_class_entry *sdl_ce = register_class_Rsdl();
	sdl_ce->default_object_handlers = &sdl_handlers;
	memcpy(&sdl_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	url_handlers.cast_object = cast_sdl;
	sdl_handlers.compare = compare_unordered;
}

/* ext/intl/resourcebundle, Zend/zend_fibers.c: a direct struct copy of the standard table. */
static void register_direct_copy(void)
{
	zend_class_entry *bundle_ce = register_class_Rbundle();
	bundle_ce->default_object_handlers = &bundle_handlers;
	bundle_handlers = std_object_handlers;
	bundle_handlers.offset = XtOffsetOf(real_object, std);
	bundle_handlers.compare = compare_unordered;
}

/* Aggregates: a positional const table, a designated table and a zeroed table with a later write. */
static const zend_object_handlers positional_handlers = {
	XtOffsetOf(real_object, std),
	NULL,
	cast_long,
	NULL,
	compare_throwing,
};
static const zend_object_handlers designated_handlers = {
	.offset = XtOffsetOf(real_object, std),
	.cast_object = cast_string,
	.compare = compare_unordered,
};
static zend_object *positional_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &positional_handlers;
	return &intern->std;
}
static zend_object *designated_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &designated_handlers;
	return &intern->std;
}
static zend_object *zero_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &zero_handlers;
	return &intern->std;
}

/* A copy is a snapshot at its copy point; a child with no creator of its own takes its parent's. */
static zend_object *base_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &base_handlers;
	return &intern->std;
}
static zend_object *snap_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &snap_handlers;
	return &intern->std;
}
static void register_snapshot(void)
{
	zend_class_entry *base_ce = register_class_Rbase();
	base_ce->create_object = base_new;
	memcpy(&base_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	memcpy(&snap_handlers, &base_handlers, sizeof(zend_object_handlers));
	base_handlers.cast_object = cast_string;
	zend_class_entry *snap_ce = register_class_Rsnap();
	snap_ce->create_object = snap_new;
	register_class_Rchild(base_ce);
}

/* A pointer alias taken after the table is initialized writes the aliased table. */
static zend_object *alias_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &alias_handlers;
	return &intern->std;
}
static void register_alias(void)
{
	zend_class_entry *alias_ce = register_class_Ralias();
	alias_ce->create_object = alias_new;
	memcpy(&alias_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	zend_object_handlers *table = &alias_handlers;
	table->cast_object = cast_long;
}

/* A slot assigned NULL in one source configuration and a function in the other. */
static zend_object *cond_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &cond_handlers;
	return &intern->std;
}
static void register_conditional(void)
{
	zend_class_entry *cond_ce = register_class_Rcond();
	cond_ce->create_object = cond_new;
	memcpy(&cond_handlers, &std_object_handlers, sizeof(zend_object_handlers));
#ifdef REAL_NO_CAST
	cond_handlers.cast_object = NULL;
#else
	cond_handlers.cast_object = cast_long;
#endif
}

/* ext/tidy/tidy.c: one creator helper, the table a parameter of it, each class creator fixing it. */
static zend_object *tidy_object_new(zend_class_entry *class_type, const zend_object_handlers *handlers)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), class_type);
	intern->std.handlers = handlers;
	return &intern->std;
}
static zend_object *tidy_doc_new(zend_class_entry *class_type)
{
	return tidy_object_new(class_type, &tidy_doc_handlers);
}
static zend_object *tidy_node_new(zend_class_entry *class_type)
{
	return tidy_object_new(class_type, &tidy_node_handlers);
}
static void register_helper_argument(void)
{
	zend_class_entry *doc_ce = register_class_Rtidya();
	doc_ce->create_object = tidy_doc_new;
	zend_class_entry *node_ce = register_class_Rtidyb();
	node_ce->create_object = tidy_node_new;
	memcpy(&tidy_doc_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	memcpy(&tidy_node_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	tidy_doc_handlers.cast_object = cast_long;
	tidy_node_handlers.cast_object = cast_string;
}

/* ext/mysqli/mysqli.c: one creator picks the table by the class of the new object. */
static zend_object *link_object_new(zend_class_entry *class_type)
{
	const zend_object_handlers *handlers;
	real_link *intern = zend_object_alloc(sizeof(real_link), class_type);
	if (instanceof_function(class_type, link_ce)) {
		handlers = &link_handlers;
	} else if (instanceof_function(class_type, stmt_ce)) {
		handlers = &stmt_handlers;
	} else {
		handlers = &plain_link_handlers;
	}
	intern->zo.handlers = handlers;
	return &intern->zo;
}
static void register_class_chain(void)
{
	link_ce->create_object = link_object_new;
	stmt_ce->create_object = link_object_new;
	zend_class_entry *child_ce = register_class_Rlinkchild(link_ce);
	child_ce->create_object = link_object_new;
	zend_class_entry *other_ce = register_class_Rother();
	other_ce->create_object = link_object_new;
	memcpy(&link_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	memcpy(&stmt_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	memcpy(&plain_link_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	link_handlers.cast_object = cast_long;
	stmt_handlers.cast_object = cast_string;
}

/* ext/gmp/gmp.c, ext/ffi/ffi.c: operations whose result is an object, or a number or an object. */
static int gmp_operation(zend_uchar opcode, zval *result, zval *op1, zval *op2)
{
	zend_object *created = zend_objects_new(NULL);
	ZVAL_OBJ(result, created);
	return SUCCESS;
}
static int cdata_operation(zend_uchar opcode, zval *result, zval *op1, zval *op2)
{
	zend_object *created;
	switch (opcode) {
		case ZEND_ADD:
			created = zend_objects_new(NULL);
			ZVAL_OBJ(result, created);
			return SUCCESS;
		case ZEND_SUB:
			if (Z_LVAL_P(op2)) {
				ZVAL_LONG(result, 1);
				return SUCCESS;
			}
			created = zend_objects_new(NULL);
			ZVAL_OBJ(result, created);
			return SUCCESS;
		default:
			return FAILURE;
	}
}
static int cdata_free_cast(zend_object *readobj, zval *retval, int type)
{
	zend_throw_error(NULL, "Attempt to use a freed object");
	return FAILURE;
}
static zend_object *gmp_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &gmp_handlers;
	return &intern->std;
}
static zend_object *cdata_new(zend_class_entry *ce)
{
	real_cdata *cdata = zend_object_alloc(sizeof(real_cdata), ce);
	cdata->std.handlers = &cdata_handlers;
	return &cdata->std;
}
/* ext/ffi/ffi.c: the table follows the kind of the type; the pointer-copy variant writes none. */
static void cdata_into_value(real_cdata *cdata, zend_long kind)
{
	cdata->std.handlers = (kind < 3) ? &cdata_value_handlers : &cdata_handlers;
}
static void cdata_pointer_free(real_cdata *cdata, void *ptr)
{
	cdata->ptr = ptr;
}
static void cdata_release(real_cdata *cdata)
{
	cdata->std.handlers = &cdata_free_handlers;
}
static void register_object_results(void)
{
	zend_class_entry *gmp_ce = register_class_Rgmp();
	gmp_ce->create_object = gmp_new;
	memcpy(&gmp_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	gmp_handlers.do_operation = gmp_operation;
	zend_class_entry *cdata_ce = register_class_Rcdata();
	cdata_ce->create_object = cdata_new;
	memcpy(&cdata_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	cdata_handlers.do_operation = cdata_operation;
	memcpy(&cdata_value_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	memset(&cdata_free_handlers, 0, sizeof(zend_object_handlers));
	cdata_free_handlers.cast_object = cdata_free_cast;
}

/* ext/com_dotnet/com_handlers.c: the converted value is the result unless the conversion failed. */
static zend_object *com_wrap_variant(VARIANT *v)
{
	return zend_objects_new(NULL);
}
static void com_zval_from_variant(zval *z, VARIANT *v)
{
	switch (V_VT(v)) {
		case VT_I8:
			ZVAL_LONG(z, v->value);
			break;
		case VT_BSTR:
			ZVAL_STR(z, NULL);
			break;
		default:
			ZVAL_OBJ(z, com_wrap_variant(v));
	}
}
static int com_cast(zend_object *readobj, zval *writeobj, int type)
{
	zend_long res = S_OK;
	zend_long wanted = VT_EMPTY;
	VARIANT v;
	ZVAL_NULL(writeobj);
	VariantCopy(&v, &v);
	switch (type) {
		case IS_LONG:
			wanted = VT_I8;
			break;
		case IS_STRING:
			wanted = VT_BSTR;
			break;
		default:
			;
	}
	if (wanted != VT_EMPTY && wanted != V_VT(&v)) {
		res = VariantChangeType(&v, &v, 0, wanted);
	}
	if (SUCCEEDED(res)) {
		com_zval_from_variant(writeobj, &v);
		return SUCCESS;
	}
	return zend_std_cast_object_tostring(readobj, writeobj, type);
}
static zend_object *com_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &com_handlers;
	return &intern->std;
}
static void register_variant_like(void)
{
	zend_class_entry *com_ce = register_class_Rcom();
	com_ce->create_object = com_new;
	memcpy(&com_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	com_handlers.cast_object = com_cast;
}

/* Final writes: the last write to the output decides, through an alias and through a helper chain. */
static void fill_inner(zval *out)
{
	ZVAL_LONG(out, 1);
}
static void fill_long(zval *out)
{
	fill_inner(out);
}
static int conv_cast(zend_object *readobj, zval *retval, int type)
{
	zval *out = retval;
	ZVAL_STR(out, NULL);
	switch (type) {
		case IS_LONG:
			fill_long(retval);
			return SUCCESS;
		case IS_STRING:
			ZVAL_BOOL(retval, 1);
			ZVAL_STR(retval, NULL);
			return SUCCESS;
		default:
			ZVAL_BOOL(retval, 1);
			return SUCCESS;
	}
}
/* A helper that calls itself has no proof of its last write: the fact is omitted and the omission reported. */
static void fill_deep(zval *out, int depth)
{
	if (depth > 0) {
		fill_deep(out, depth - 1);
		return;
	}
	ZVAL_LONG(out, 1);
}
static int rec_cast(zend_object *readobj, zval *retval, int type)
{
	fill_deep(retval, 3);
	return SUCCESS;
}
static zend_object *rec_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &rec_handlers;
	return &intern->std;
}
static zend_object *conv_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &conv_handlers;
	return &intern->std;
}

/* A pending exception is no normal result, whatever the function returns. */
static int exc_cast(zend_object *readobj, zval *retval, int type)
{
	if (type == IS_LONG) {
		zend_throw_error(NULL, "no integer");
		return SUCCESS;
	}
	ZVAL_LONG(retval, 1);
	return SUCCESS;
}
static zend_object *exc_new(zend_class_entry *ce)
{
	real_object *intern = zend_object_alloc(sizeof(real_object), ce);
	intern->std.handlers = &exc_handlers;
	return &intern->std;
}
static void register_final_writes(void)
{
	zend_class_entry *conv_ce = register_class_Rconv();
	conv_ce->create_object = conv_new;
	memcpy(&conv_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	conv_handlers.cast_object = conv_cast;
	zend_class_entry *exc_ce = register_class_Rexc();
	exc_ce->create_object = exc_new;
	memcpy(&exc_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	exc_handlers.cast_object = exc_cast;
	zend_class_entry *rec_ce = register_class_Rrec();
	rec_ce->create_object = rec_new;
	memcpy(&rec_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	rec_handlers.cast_object = rec_cast;
}

int zm_startup_real(int type, int module_number)
{
	register_soap_like();
	register_direct_copy();
	zend_class_entry *positional_ce = register_class_Rpos();
	positional_ce->create_object = positional_new;
	zend_class_entry *designated_ce = register_class_Rdes();
	designated_ce->create_object = designated_new;
	zend_class_entry *zero_ce = register_class_Rzero();
	zero_ce->create_object = zero_new;
	memset(&zero_handlers, 0, sizeof(zend_object_handlers));
	zero_handlers.cast_object = cast_long;
	register_snapshot();
	register_alias();
	register_conditional();
	register_helper_argument();
	link_ce = register_class_Rlink();
	stmt_ce = register_class_Rstmt();
	register_class_chain();
	register_object_results();
	register_variant_like();
	register_final_writes();
	register_class_Rface();
	register_class_Renum(NULL);
	register_class_Rfinal();
	return SUCCESS;
}
