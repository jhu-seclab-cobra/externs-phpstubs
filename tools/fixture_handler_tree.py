"""A small php-src tree for the handler extraction tests: the value tags, the handler struct, the standard table, the
engine's calls of the cast, compare and operation handlers, and one extension that registers classes whose creators
take tables of every shape the extraction follows (design-extraction-handlers.md).

``write_tree(root)`` writes the tree below a directory; ``replaced`` swaps or adds files.
"""

from pathlib import Path
TYPES_H = """
#define IS_UNDEF 0
#define IS_NULL 1
#define IS_FALSE 2
#define IS_TRUE 3
#define IS_LONG 4
#define IS_DOUBLE 5
#define IS_STRING 6
#define IS_ARRAY 7
#define IS_OBJECT 8
#define IS_RESOURCE 9
#define _IS_BOOL 18
#define _IS_NUMBER 19
#define SUCCESS 0
#define FAILURE -1
#define Z_TYPE_INFO(zval) (zval).u1.type_info
#define Z_TYPE_INFO_P(zval_p) Z_TYPE_INFO(*(zval_p))
#define Z_TYPE_P(zval_p) (Z_TYPE_INFO_P(zval_p) & 0xff)
#define Z_LVAL(zval) (zval).value.lval
#define Z_LVAL_P(zval_p) Z_LVAL(*(zval_p))
#define Z_STR(zval) (zval).value.str
#define Z_STR_P(zval_p) Z_STR(*(zval_p))
#define ZVAL_NULL(z) do { Z_TYPE_INFO_P(z) = IS_NULL; } while (0)
#define ZVAL_FALSE(z) do { Z_TYPE_INFO_P(z) = IS_FALSE; } while (0)
#define ZVAL_TRUE(z) do { Z_TYPE_INFO_P(z) = IS_TRUE; } while (0)
#define ZVAL_BOOL(z, b) do { Z_TYPE_INFO_P(z) = (b) ? IS_TRUE : IS_FALSE; } while (0)
#define ZVAL_LONG(z, l) do { zval *__z = (z); Z_LVAL_P(__z) = l; Z_TYPE_INFO_P(__z) = IS_LONG; } while (0)
#define ZVAL_STR(z, s) do { zval *__z = (z); Z_STR_P(__z) = (s); Z_TYPE_INFO_P(__z) = IS_STRING; } while (0)
#define Z_OBJ_P(zval_p) ((zval_p)->value.obj)
#define Z_OBJ_HT_P(zval_p) (Z_OBJ_P(zval_p)->handlers)
#define ZVAL_UNDEF(z) do { Z_TYPE_INFO_P(z) = IS_UNDEF; } while (0)
struct _zend_object {
	zend_class_entry *ce;
	const zend_object_handlers *handlers;
};
"""

HANDLERS_H = """
struct _zend_object_handlers {
	int offset;
	zend_object_free_obj_t free_obj;
	zend_object_cast_t cast_object;
	zend_object_do_operation_t do_operation;
	zend_object_compare_t compare;
};
extern const ZEND_API zend_object_handlers std_object_handlers;
"""

API_H = """
#define INIT_CLASS_ENTRY(class_container, class_name, functions) \\
	INIT_CLASS_ENTRY_EX(class_container, class_name, strlen(class_name), functions)
#define INIT_CLASS_ENTRY_EX(class_container, class_name, class_name_len, functions) \\
	{ \\
		memset(&class_container, 0, sizeof(zend_class_entry)); \\
		class_container.name = zend_string_init_interned(class_name, class_name_len, 1); \\
		class_container.default_object_handlers = &std_object_handlers; \\
	}
"""

OPCODES_H = """
#define ZEND_ADD 1
#define ZEND_SUB 2
#define ZEND_CONCAT 8
"""

STD_C = """
static int std_cast(zend_object *readobj, zval *retval, int type)
{
	zend_string *string;
	switch (type) {
		case IS_STRING:
			ZVAL_STR(retval, string);
			return SUCCESS;
		default:
			return FAILURE;
	}
}
static int std_compare(zval *o1, zval *o2)
{
	return 1;
}
ZEND_API const zend_object_handlers std_object_handlers = {
	0,
	NULL,
	std_cast,
	NULL,
	std_compare,
};
ZEND_API zend_object *zend_objects_new(zend_class_entry *ce)
{
	zend_object *object = emalloc(sizeof(zend_object));
	object->ce = ce;
	object->handlers = ce->default_object_handlers;
	return object;
}
"""

ENGINE_C = """
void engine_convert(zval *op, zval *dst)
{
	if (Z_OBJ_HT_P(op)->cast_object(Z_OBJ_P(op), dst, IS_STRING) == SUCCESS) {
		return;
	}
	if (Z_OBJ_HT_P(op)->cast_object(Z_OBJ_P(op), dst, IS_LONG) == SUCCESS) {
		return;
	}
	if (Z_OBJ_HT_P(op)->cast_object(Z_OBJ_P(op), dst, _IS_BOOL) == SUCCESS) {
		return;
	}
}
void engine_add(zval *a, zval *b, zval *result)
{
	Z_OBJ_HT_P(a)->do_operation(ZEND_ADD, result, a, b);
	Z_OBJ_HT_P(a)->do_operation(ZEND_SUB, result, a, b);
}
int engine_compare(zval *a, zval *b)
{
	return Z_OBJ_HT_P(a)->compare(a, b);
}
"""

DEMO_ARGINFO = """
static zend_class_entry *register_class_Plain(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Plain", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Counter(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Counter", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, ZEND_ACC_FINAL);
	return class_entry;
}
static zend_class_entry *register_class_Viamethod(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Viamethod", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Methodfirst(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Methodfirst", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Nativefirst(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Nativefirst", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Optional(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Optional", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Zeroed(void)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Zeroed", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, NULL, 0);
	return class_entry;
}
static zend_class_entry *register_class_Pair(zend_class_entry *class_entry_Plain)
{
	zend_class_entry ce, *class_entry;
	INIT_CLASS_ENTRY(ce, "Pair", NULL);
	class_entry = zend_register_internal_class_with_flags(&ce, class_entry_Plain, 0);
	return class_entry;
}
"""

DEMO_C = """
#include "demo_arginfo.h"
typedef struct _counter_object {
	zend_long count;
	zend_object std;
} counter_object;
static zend_object_handlers counter_handlers;
static zend_object_handlers first_handlers, second_handlers;
struct other_ops {
	int (*cast_object)(int);
};
static zend_object_handlers via_handlers, first_method_handlers, first_native_handlers;
static zend_object_handlers optional_handlers, zeroed_handlers;
static zend_class_entry *counter_ce;
static zend_class_entry *pair_ce;

static int counter_cast(zend_object *readobj, zval *retval, int type)
{
	switch (type) {
		case IS_LONG:
			ZVAL_LONG(retval, 1);
			return SUCCESS;
		case _IS_BOOL:
			ZVAL_TRUE(retval);
			return SUCCESS;
		case IS_STRING:
			ZVAL_STR(retval, NULL);
			return SUCCESS;
		default:
			return FAILURE;
	}
}
static int counter_operation(zend_uchar opcode, zval *result, zval *op1, zval *op2)
{
	switch (opcode) {
		case ZEND_ADD:
			ZVAL_LONG(result, 2);
			return SUCCESS;
		case ZEND_SUB:
			ZVAL_BOOL(result, Z_LVAL_P(op1));
			return SUCCESS;
		default:
			return FAILURE;
	}
}
static int via_cast(zend_object *readobj, zval *retval, int type)
{
	zend_class_entry *ce = readobj->ce;
	if (type == IS_STRING && ce->__tostring) {
		zend_call_known_instance_method_with_0_params(ce->__tostring, readobj, retval);
		return SUCCESS;
	}
	return FAILURE;
}
static int method_first_cast(zend_object *readobj, zval *retval, int type)
{
	zend_class_entry *ce = readobj->ce;
	if (type != IS_STRING) {
		return FAILURE;
	}
	if (ce->__tostring) {
		zend_call_known_instance_method_with_0_params(ce->__tostring, readobj, retval);
	}
	ZVAL_STR(retval, NULL);
	return SUCCESS;
}
static int native_first_cast(zend_object *readobj, zval *retval, int type)
{
	zend_class_entry *ce = readobj->ce;
	if (type != IS_STRING) {
		return FAILURE;
	}
	ZVAL_STR(retval, NULL);
	if (ce->__tostring) {
		zend_call_known_instance_method_with_0_params(ce->__tostring, readobj, retval);
	}
	return SUCCESS;
}
static zend_object *via_new(zend_class_entry *ce)
{
	zend_object *object = zend_objects_new(ce);
	object->handlers = &via_handlers;
	return object;
}
static zend_object *method_first_new(zend_class_entry *ce)
{
	zend_object *object = zend_objects_new(ce);
	object->handlers = &first_method_handlers;
	return object;
}
static zend_object *native_first_new(zend_class_entry *ce)
{
	zend_object *object = zend_objects_new(ce);
	object->handlers = &first_native_handlers;
	return object;
}
static int pair_cast(zend_object *readobj, zval *retval, int type)
{
	zend_throw_error(NULL, "no conversion");
	return FAILURE;
}
static int pair_compare(zval *o1, zval *o2)
{
	return 0;
}
static zend_object *counter_new(zend_class_entry *ce)
{
	counter_object *intern = zend_object_alloc(sizeof(counter_object), ce);
	intern->std.ce = ce;
	intern->std.handlers = &counter_handlers;
	return &intern->std;
}
static zend_object *optional_new(zend_class_entry *ce)
{
	zend_object *object = zend_objects_new(ce);
	object->handlers = &optional_handlers;
	return object;
}
static zend_object *zeroed_new(zend_class_entry *ce)
{
	zend_object *object = zend_objects_new(ce);
	object->handlers = &zeroed_handlers;
	return object;
}
static zend_object *pair_new(zend_class_entry *ce)
{
	zend_object *object = zend_objects_new(ce);
	object->handlers = &second_handlers;
	return object;
}
static void unrelated(struct other_ops *thing)
{
	thing->cast_object = NULL;
}
struct document_holder {
	struct document_ops *handlers;
};
static const zend_object_handlers later_handlers = {
	0,
	NULL,
	counter_cast,
	NULL,
	NULL,
};
static void copy_counter(counter_object *intern, counter_object *other)
{
	intern->std.handlers = other->std.handlers;
}
static void retarget_counter(counter_object *intern)
{
	intern->std.handlers = &later_handlers;
}
static void bind_document(struct document_holder *holder)
{
	holder->handlers = NULL;
}
int zm_startup_demo(int type, int module_number)
{
	counter_ce = register_class_Counter();
	counter_ce->create_object = counter_new;
	memcpy(&counter_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	counter_handlers.cast_object = counter_cast;
	counter_handlers.do_operation = counter_operation;
	counter_handlers.compare = NULL;
	pair_ce = register_class_Pair(register_class_Plain());
	pair_ce->create_object = pair_new;
	memcpy(&first_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	first_handlers.cast_object = pair_cast;
	memcpy(&second_handlers, &first_handlers, sizeof(zend_object_handlers));
	second_handlers.compare = pair_compare;
	zend_class_entry *zeroed_ce = register_class_Zeroed();
	zeroed_ce->create_object = zeroed_new;
	memset(&zeroed_handlers, 0, sizeof(zend_object_handlers));
	zeroed_handlers.cast_object = counter_cast;
	zend_class_entry *optional_ce = register_class_Optional();
	optional_ce->create_object = optional_new;
	memcpy(&optional_handlers, &std_object_handlers, sizeof(zend_object_handlers));
#ifdef FEATURE_COMPARE
	optional_handlers.compare = pair_compare;
#endif
	zend_class_entry *via_ce = register_class_Viamethod();
	via_ce->create_object = via_new;
	memcpy(&via_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	via_handlers.cast_object = via_cast;
	zend_class_entry *method_ce = register_class_Methodfirst();
	method_ce->create_object = method_first_new;
	memcpy(&first_method_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	first_method_handlers.cast_object = method_first_cast;
	zend_class_entry *native_ce = register_class_Nativefirst();
	native_ce->create_object = native_first_new;
	memcpy(&first_native_handlers, &std_object_handlers, sizeof(zend_object_handlers));
	first_native_handlers.cast_object = native_first_cast;
	return SUCCESS;
}
"""


FILES = {
    "Zend/zend_types.h": TYPES_H,
    "Zend/zend_object_handlers.h": HANDLERS_H,
    "Zend/zend_API.h": API_H,
    "Zend/zend_vm_opcodes.h": OPCODES_H,
    "Zend/zend_object_handlers.c": STD_C,
    "Zend/zend_operators.c": ENGINE_C,
    "ext/demo/demo_arginfo.h": DEMO_ARGINFO,
    "ext/demo/demo.c": DEMO_C,
}


def write_tree(root, replaced=None):
    """Write the tree below ``root``; a path in ``replaced`` takes the given text instead, or is added."""
    for name, text in {**FILES, **(replaced or {})}.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
