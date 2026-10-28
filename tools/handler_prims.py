"""The functions the handler machine implements itself: allocation, memory copies, class registration, exceptions and
the call of a class's string-conversion method (design-extraction-handlers.md)."""

from handler_memory import ANYV, ZERO, Alt, Fill, Ptr, Size, Str, Sym
from handler_values import narrow, truth

EXCEPTION = ("exception",)
EXCEPTIONS_REGION = "g:executor_globals"
METHOD_RESULT = Sym("m:result")
ZEROED = {"ecalloc", "pecalloc", "calloc"}
ALLOCATORS = ZEROED | {"zend_object_alloc", "emalloc", "pemalloc", "malloc", "safe_emalloc", "safe_pemalloc", "emalloc_large"}
NOOPS = {
    "zval_ptr_dtor", "zval_ptr_dtor_nogc", "zval_dtor", "zend_string_release", "zend_string_release_ex",
    "zend_string_addref", "efree", "efree_size", "efree_large", "efree_huge", "pefree", "pefree_size", "free", "zend_object_release", "zend_objects_store_put",
    "zend_update_class_constants", "zend_bailout_check",
}
# The in-place conversions and the type tags the converted zval can have afterwards.
CONVERSIONS = {
    "convert_to_string": ("IS_STRING",), "_convert_to_string": ("IS_STRING",), "convert_to_long": ("IS_LONG",),
    "convert_to_double": ("IS_DOUBLE",), "convert_to_boolean": ("IS_TRUE", "IS_FALSE"), "convert_to_array": ("IS_ARRAY",),
    "convert_to_object": ("IS_OBJECT",), "convert_to_null": ("IS_NULL",),
    "convert_scalar_to_number": ("IS_LONG", "IS_DOUBLE"),
}
TYPE_INFO = ("u1", "type_info")
METHOD_CALLS = {
    "zend_call_known_instance_method", "zend_call_known_instance_method_with_0_params",
    "zend_call_known_instance_method_with_1_params", "zend_call_known_instance_method_with_2_params",
}


class Primitives:
    """Mixin of the machine: ``p_<name>(args, state, frame)`` returns the (value, state) outcomes of the call."""

    def p_EXPECTED(self, args, state, frame):
        return [(args[0], state)]

    p_UNEXPECTED = p_LIKELY = p_UNLIKELY = p___builtin_expect = p_EXPECTED

    def p_ZEND_ASSERT(self, args, state, frame):
        """An assertion holds on every path the machine follows: a path where it fails is dropped."""
        if truth(args[0], state) is False:
            return []
        narrow(args[0], True, state)
        return [(ANYV, state)]

    p_ZEND_ASSUME = p_assert = p_ZEND_ASSERT

    def p_ZEND_UNREACHABLE(self, args, state, frame):
        return []

    def p_memcpy(self, args, state, frame):
        destination, source = args[0], args[1]
        if isinstance(destination, Ptr) and isinstance(source, Ptr):
            state.write_tree(destination.rid, destination.path, state.tree(source.rid, source.path))
        elif isinstance(destination, Ptr):
            state.havoc(destination.rid, destination.path)
        return [(destination, state)]

    p_memmove = p_memcpy

    def p_memset(self, args, state, frame):
        destination = args[0]
        if isinstance(destination, Ptr):
            if args[1] == 0:
                state.write(destination.rid, destination.path, ZERO)
            else:
                state.havoc(destination.rid, destination.path)
        return [(destination, state)]

    def allocate(self, name, args, state, frame):
        kind = args[0].type_name if args and isinstance(args[0], Size) else None
        return [(Ptr(state.allocate(0 if name in ZEROED else ANYV, kind), ()), state)]

    def __getattr__(self, name):
        if name.startswith("p_"):
            kind = name[2:]
            if kind in ALLOCATORS:
                return lambda args, state, frame: self.allocate(kind, args, state, frame)
            if kind in NOOPS:
                return lambda args, state, frame: [(ANYV, state)]
            if kind in CONVERSIONS:
                return lambda args, state, frame: self.convert(CONVERSIONS[kind], args, state)
            if kind in METHOD_CALLS:
                return self.p_call_method
        raise AttributeError(name)

    def convert(self, targets, args, state):
        """An in-place conversion of a zval: where unread calls matter, the zval afterwards has one of the target
        type tags and an unknown value; elsewhere it is an unknown call."""
        zval = args[0] if args else None
        if not (isinstance(zval, Ptr) and self.policy.unread_writes(zval)):
            return self.unknown_call(args, state)
        state.write(zval.rid, zval.path, Fill(ANYV))
        tags = [self.index.tags[name] for name in targets]
        state.write(zval.rid, zval.path + TYPE_INFO, tags[0] if len(tags) == 1 else Alt(tuple((t, ()) for t in tags)))
        return [(ANYV, state)]

    def p_zend_string_init_interned(self, args, state, frame):
        return [(args[0], state)]

    def p_zend_clear_exception(self, args, state, frame):
        state.write(EXCEPTIONS_REGION, EXCEPTION, 0)
        return [(ANYV, state)]

    def p_throw(self, args, state, frame):
        state.write(EXCEPTIONS_REGION, EXCEPTION, 1)
        return [(ANYV, state)]

    def p_call_method(self, args, state, frame):
        """A call of a method through the marker pointer stands for the user method: its result is unknown and it
        was run (the call is event M); any other target is an unknown call."""
        output = args[2] if len(args) > 2 else None
        if args[0] != self.marker or not isinstance(output, Ptr):
            return self.unknown_call(args, state)
        state.write(output.rid, output.path, Fill(METHOD_RESULT))
        return [(ANYV, state)]

    # -- class registration ------------------------------------------------------------------------------------
    def p_zend_register_internal_class_ex(self, args, state, frame):
        return self.register(args[0], args[1] if len(args) > 1 else 0, state)

    def p_zend_register_internal_class(self, args, state, frame):
        return self.register(args[0], 0, state)

    def p_zend_register_internal_class_with_flags(self, args, state, frame):
        return self.register(args[0], args[1], state)

    def p_zend_register_internal_interface(self, args, state, frame):
        return self.register(args[0], 0, state)

    def register(self, entry, parent, state):
        """Copy a class entry into the region of its class and let it inherit its parent's object creation."""
        name = self.class_name(entry, state)
        if name is None or not isinstance(entry, Ptr):
            return [(ANYV, state)]
        rid = "c:" + name
        state.write_tree(rid, (), state.tree(entry.rid, entry.path))
        self.inherit(Ptr(rid, ()), parent, state)
        return [(Ptr(rid, ()), state)]

    def p_zend_do_inheritance_ex(self, args, state, frame):
        self.inherit(args[0], args[1], state)
        return [(0, state)]

    p_zend_do_inheritance = p_zend_do_inheritance_ex

    @staticmethod
    def inherit(entry, parent, state):
        """The engine copies the parent's create_object and default_object_handlers into a class unconditionally."""
        if isinstance(parent, Sym):
            parent = parent.pointer()
        if not isinstance(entry, Ptr) or not isinstance(parent, Ptr):
            return
        for field in ("create_object", "default_object_handlers"):
            state.write(entry.rid, entry.path + (field,), state.read(parent.rid, parent.path + (field,)))

    def class_name(self, entry, state):
        """The folded name of the class a class entry names, or None."""
        if not isinstance(entry, Ptr):
            return None
        name = state.read(entry.rid, entry.path + ("name",))
        folded = self.index.program.string(name).lower() if isinstance(name, Str) else ""
        return folded or None
