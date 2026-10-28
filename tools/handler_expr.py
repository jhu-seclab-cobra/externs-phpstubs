"""Expression evaluation of the handler extraction (design-extraction-handlers.md).

``ev`` returns every (value, state) outcome of an expression; an outcome that forks the path owns a forked state, so a
caller continues only from the returned states. ``lv`` returns the (location, state) outcomes of an lvalue."""

from handler_memory import ANYV, Agg, Size, Alt, Fn, Masked, Ptr, Str, Sym, ZERO, alternatives
from handler_values import binary, cast, literals, narrow, resolve, truth

FORK_CAP = 48
NULL_NAMES = {"NULL": 0, "nullptr": 0, "false": 0, "true": 1}
OFFSET_NAMES = {"XtOffsetOf", "offsetof", "__builtin_offsetof"}
PAYLOAD = "value"


def alias(path):
    """The cell a field path denotes and the bits of it the path reads: ``u1.v.type`` is the low byte of
    ``u1.type_info`` and every member of ``value`` is one payload cell."""
    if path[-3:] == ("u1", "v", "type"):
        return path[:-3] + ("u1", "type_info"), 0xFF
    if PAYLOAD in path:
        return path[:path.index(PAYLOAD) + 1], -1
    return path, -1


def masked(value, mask):
    if mask == -1:
        return value
    if isinstance(value, Alt):
        return Alt(tuple((masked(v, mask), c) for v, c in value.items))
    if isinstance(value, int):
        return value & mask
    if isinstance(value, Sym):
        return Masked(value, mask)
    if isinstance(value, Masked):
        return Masked(value.sym, value.mask & mask)
    return ANYV


def type_name(words):
    """The type a sizeof names: its last word that is not a keyword or a qualifier; None for an expression."""
    names = [w for w in words if w.isidentifier() and w not in ("struct", "union", "const", "unsigned")]
    return names[-1] if names and "*" not in words else None


class Expressions:
    """The expression half of the machine; ``Machine`` supplies the index, the primitives and the call mechanism."""

    def alts(self, value, state):
        """Fork a state over the alternatives of a value; an alternative holding under source conditions adds them."""
        items = alternatives(value) if isinstance(value, Alt) else ((value, ()),)
        out = []
        for k, (plain, conditions) in enumerate(items[:FORK_CAP]):
            fork = state if k == len(items[:FORK_CAP]) - 1 else state.fork()
            fork.tags = fork.tags | frozenset(conditions)
            out.append((plain, fork))
        return out

    def load(self, pointer, state):
        if isinstance(pointer, Sym):
            pointer = pointer.pointer()
        if not isinstance(pointer, Ptr):
            return ANYV
        path, mask = alias(pointer.path)
        return masked(state.read(pointer.rid, path), mask)

    def store(self, pointer, value, state):
        if isinstance(pointer, Sym):
            pointer = pointer.pointer()
        if not isinstance(pointer, Ptr):
            return
        path, mask = alias(pointer.path)
        if mask != -1:
            old = state.read(pointer.rid, path)
            if isinstance(old, int) and isinstance(value, int):
                value = (old & ~mask) | (value & mask)
        state.write(pointer.rid, path, value)

    def ev(self, node, state, frame):
        return getattr(self, "e_" + node[0])(node, state, frame)

    def e_num(self, node, state, frame):
        return [(node[1], state)]

    def e_str(self, node, state, frame):
        return [(Str(node[1]), state)]

    def e_unknown(self, node, state, frame):
        return [(ANYV, state)]

    def e_sizeof(self, node, state, frame):
        return [(Size(self.sized_type(node[1], frame)), state)]

    @staticmethod
    def sized_type(words, frame):
        """The type a sizeof names: a type, or the declared type of the variable ``v`` or ``*v``."""
        variable = words[-1] if len(words) == 1 or (len(words) == 2 and words[0] == "*") else None
        return frame.types.get(variable) if variable in frame.types else type_name(words)

    def e_name(self, node, state, frame):
        name = node[1]
        if name in frame.vars:
            if name in frame.arrays:
                return [(Ptr(frame.vars[name], (0,)), state)]
            return [(state.read(frame.vars[name], ()), state)]
        constant = self.constant_of(name, frame)
        if constant is not None:
            return [(constant, state)]
        return [(self.load(self.global_ptr(name, frame), state), state)]

    def constant_of(self, name, frame):
        if name in NULL_NAMES:
            return NULL_NAMES[name]
        value = self.index.constant(name, frame.source)
        if value is not None:
            return value
        definition = self.index.definitions(name, frame.source)
        return Fn(name, definition[0].source.relative) if definition else None

    def global_ptr(self, name, frame):
        region = self.index.table_region(name, frame.source)
        return Ptr(region or f"g:{name}", ())

    def e_member(self, node, state, frame):
        return [(self.load(p, s), s) for p, s in self.lv(node, state, frame)]

    def e_index(self, node, state, frame):
        return [(self.load(p, s), s) for p, s in self.lv(node, state, frame)]

    def e_comma(self, node, state, frame):
        return [out for _, s in self.ev(node[1], state, frame) for out in self.ev(node[2], s, frame)]

    def e_stmtexpr(self, node, state, frame):
        return self.run_inline(node[1], state, frame)

    def e_init(self, node, state, frame):
        return [(self.initializer(node, None, state, frame), state)]

    def e_cast(self, node, state, frame):
        out = []
        for value, s in self.ev(node[2], state, frame):
            for plain, s2 in self.alts(value, s):
                out.append((self.retype(node[1], cast(node[1], plain), s2), s2))
        return out

    def retype(self, words, value, state):
        """A pointer cast between a struct and the zend_object that opens it denotes the same location: the pointer
        moves between the struct's address and its object member's."""
        if not isinstance(value, Ptr) or "*" not in words:
            return value
        region = state.region(value.rid)
        member = self.index.embedded.get(region.kind) if region is not None else None
        if member is None:
            return value
        target = type_name([w for w in words if w != "*"])
        if target == "zend_object" and value.path == ():
            return Ptr(value.rid, (member,))
        if target == region.kind and value.path == (member,):
            return Ptr(value.rid, ())
        return value

    def e_un(self, node, state, frame):
        operator = node[1]
        if operator == "&":
            return [(p, s) for p, s in self.lv(node[2], state, frame)]
        if operator == "*":
            return [(self.load(p, s), s) for p, s in self.lv(node, state, frame)]
        if operator == "!":
            return self.e_not(node, state, frame)
        out = []
        for value, s in self.ev(node[2], state, frame):
            out.append((self.unary(operator, resolve(value, s)), s))
        return out

    @staticmethod
    def unary(operator, value):
        if not isinstance(value, int):
            return ANYV
        return {"-": -value, "+": value, "~": ~value}.get(operator, ANYV)

    def e_not(self, node, state, frame):
        return [(int(not taken), s) for taken, s in self.branch(node[2], state, frame)]

    def e_bin(self, node, state, frame):
        operator = node[1]
        if operator in ("&&", "||"):
            return [(int(taken), s) for taken, s in self.branch(node, state, frame)]
        out = []
        for left, s1 in self.ev(node[2], state, frame):
            for right, s2 in self.ev(node[3], s1, frame):
                out.extend(self.apply_binary(operator, left, right, s2))
        return out

    def apply_binary(self, operator, left, right, state):
        out = []
        for a, s1 in self.alts(left, state):
            for b, s2 in self.alts(right, s1):
                out.append((binary(operator, a, b, s2), s2))
        return out

    def e_cond(self, node, state, frame):
        out = []
        for taken, s in self.branch(node[1], state, frame):
            out.extend(self.ev(node[2] if taken else node[3], s, frame))
        return out

    def e_post(self, node, state, frame):
        out = []
        for pointer, s in self.lv(node[2], state, frame):
            old = self.load(pointer, s)
            new = binary(node[1][0], old, 1, s)
            self.store(pointer, new, s)
            out.append((old, s))
        return out

    def e_assign(self, node, state, frame):
        _, operator, target, source = node
        if self.sites is not None and target[0] == "member":
            self.sites.add(id(node))
        out = []
        for value, s1 in self.ev(source, state, frame):
            for pointer, s2 in self.lv(target, s1, frame):
                new = value if operator == "=" else self.compound(operator, pointer, value, s2)
                self.store(pointer, new, s2)
                out.append((new, s2))
        return out

    def compound(self, operator, pointer, value, state):
        return binary(operator[:-1], self.load(pointer, state), value, state)

    def lv(self, node, state, frame):
        return getattr(self, "l_" + node[0], self.l_value)(node, state, frame)

    def l_value(self, node, state, frame):
        return [(ANYV, s) for _, s in self.ev(node, state, frame)]

    def l_name(self, node, state, frame):
        name = node[1]
        if name in frame.vars:
            return [(Ptr(frame.vars[name], ()), state)]
        return [(self.global_ptr(name, frame), state)]

    def l_member(self, node, state, frame):
        _, base, field, arrow = node
        if not arrow:
            return [(Ptr(p.rid, p.path + (field,)) if isinstance(p, Ptr) else ANYV, s)
                    for p, s in self.lv(base, state, frame)]
        out = []
        for value, s in self.ev(base, state, frame):
            for plain, s2 in self.alts(value, s):
                out.append((self.field_of(plain, field), s2))
        return out

    @staticmethod
    def field_of(pointer, field):
        if isinstance(pointer, Sym):
            pointer = pointer.pointer()
        return Ptr(pointer.rid, pointer.path + (field,)) if isinstance(pointer, Ptr) else ANYV

    def l_index(self, node, state, frame):
        out = []
        for base, s1 in self.ev(node[1], state, frame):
            for index, s2 in self.ev(node[2], s1, frame):
                for a, s3 in self.alts(base, s2):
                    out.append((binary("+", a, index, s3), s3))
        return out

    def l_un(self, node, state, frame):
        if node[1] != "*":
            return self.l_value(node, state, frame)
        out = []
        for value, s in self.ev(node[2], state, frame):
            out.extend(self.alts(value, s))
        return out

    def l_call(self, node, state, frame):
        callee = node[1]
        if callee[0] == "name" and callee[1] in self.global_accessors:
            field = node[2][0][1] if node[2] and node[2][0][0] == "name" else None
            return [(Ptr(f"g:{self.global_accessors[callee[1]]}", (field,)), state)]
        return self.l_value(node, state, frame)

    def branch(self, node, state, frame):
        """The (taken, state) outcomes of a condition; a test on an unknown value narrows the state."""
        kind = node[0]
        if kind == "un" and node[1] == "!":
            return [(not taken, s) for taken, s in self.branch(node[2], state, frame)]
        if kind == "bin" and node[1] in ("&&", "||"):
            return self.branch_logical(node, state, frame)
        out = []
        for value, s in self.ev(node, state, frame):
            for plain, s2 in self.alts(value, s):
                out.extend(self.fork_on(plain, s2))
        return out

    def branch_logical(self, node, state, frame):
        conjunction = node[1] == "&&"
        out = []
        for taken, s in self.branch(node[2], state, frame):
            if taken != conjunction:
                out.append((taken, s))
            else:
                out.extend(self.branch(node[3], s, frame))
        return out

    @staticmethod
    def fork_on(value, state):
        known_truth = truth(value, state)
        if known_truth is not None:
            return [(known_truth, state)]
        other = state.fork()
        narrow(value, True, state)
        narrow(value, False, other)
        return [(True, state), (False, other)]

    def initializer(self, node, layout, state, frame):
        """The tree of an initializer list: positional items take the layout's fields in order, designated items
        their designator; every other location is zero. An item under source conditions makes its location an
        Alt of the item under those conditions and the value the location held before the conditional group."""
        cells, position, groups = {(): ZERO}, 0, {}
        for designators, value, active in node[1]:
            path, position = self.designated(designators, layout, position)
            for relative, item in self.initial_value(value, state, frame).items():
                self.put_item(cells, groups, path + relative, item, (active, frame.source))
        for (path, _), (base, items, exhaustive) in groups.items():
            cells[path] = Alt(tuple(items) + (() if exhaustive else ((base, ()),)))
        return Agg(cells)

    @staticmethod
    def put_item(cells, groups, path, item, under):
        active, source = under
        if not active:
            cells[path] = item
            for key in [k for k in groups if k[0] == path]:
                del groups[key]
            return
        group = active[-1][0]
        conditions = tuple(sorted({c for g, b in active for c in literals(source.conditions[(g, b)])}))
        entry = groups.setdefault((path, group), (cells.get(path, 0), [], group in source.otherwise))
        entry[1].append((item, conditions))
        cells[path] = item

    @staticmethod
    def designated(designators, layout, position):
        if not designators:
            field = layout[position] if layout and position < len(layout) else position
            return (field,), position + 1
        path = tuple(d if isinstance(d, str) else d[1][1] for d in designators)
        if layout and path[0] in layout:
            position = layout.index(path[0]) + 1
        return path, position

    def initial_value(self, value, state, frame):
        if value[0] == "init":
            return dict(self.initializer(value, None, state, frame))
        results = self.ev(value, state, frame)
        plain = results[0][0] if results else ANYV
        return dict(plain) if isinstance(plain, Agg) else {(): plain}
