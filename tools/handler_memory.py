"""Abstract memory of the handler extraction (design-extraction-handlers.md).

A value is a Python int (a C integer), a ``Ptr`` (the address of one location), an ``Fn`` (a function used as a value),
a ``Str`` (a string literal), a ``Sym`` (a value the extraction does not know but can narrow and dereference), an
``Alt`` (one of several values, each under the source conditions that select it), or ``ANYV``. Memory is a set of
regions; a region maps field paths to values, with ``Fill`` cells standing for a whole subtree. A location no rule wrote
reads as the region's base value, and an unknown value is never the NULL pointer.
"""

import collections
from collections.abc import Mapping


class Unknown:
    """A value no rule knows: ANYV carries no identity, SYMBOLIC marks a region whose unwritten cells are symbols."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


ANYV, SYMBOLIC = Unknown("ANYV"), Unknown("SYMBOLIC")


class Sym(Unknown):
    """An unknown value with an identity: a test on it narrows every copy of it, and a dereference of it reads the
    symbolic region ``y:<sid>``."""

    def __init__(self, sid):
        super().__init__(sid)
        self.sid = sid

    def __eq__(self, other):
        return isinstance(other, Sym) and other.sid == self.sid

    def __hash__(self):
        return hash(self.sid)

    def pointer(self):
        return Ptr("y:" + self.sid, ())


class Masked(collections.namedtuple("Masked", "sym mask")):
    """The bits of a symbol under a mask: ``sym & mask``."""


class Test(collections.namedtuple("Test", "sym mask equal const")):
    """The unknown result of comparing the masked bits of a symbol with a constant."""


class Ptr(collections.namedtuple("Ptr", "rid path")):
    """The address of one location: a region and the field path inside it."""


class Fn(collections.namedtuple("Fn", "name source")):
    """A function named as a value: its name and the file the name resolved in."""


class Fill(collections.namedtuple("Fill", "value")):
    """Every location below the cell's path that no cell overrides reads as this value."""


class Havoc(collections.namedtuple("Havoc", "serial")):
    """A Fill value: every location below was written by code the extraction does not read, at this step."""


class Alt(collections.namedtuple("Alt", "items")):
    """One of several values: ``items`` is a tuple of (value, conditions) pairs, conditions a sorted tuple of the
    source conditions that select the value."""


class Str(str):
    """A string literal placeholder (``__STR_n__``)."""


class Agg(Mapping):
    """An immutable subtree value, compared and hashed by its relative paths and values."""

    def __init__(self, cells):
        self._cells = dict(cells)

    def __getitem__(self, path):
        return self._cells[path]

    def __iter__(self):
        return iter(self._cells)

    def __len__(self):
        return len(self._cells)

    def __hash__(self):
        return hash(frozenset(self._cells.items()))


class Size(collections.namedtuple("Size", "type_name", defaults=(None,))):
    """An unknown byte size or offset (sizeof, offsetof); its type name is its value identity. Pointer arithmetic
    with a size keeps the pointer. A sizeof of a type names it."""


SIZE = Size()
ZERO = Fill(0)
ALT_CAP = 16
NATIVE_EVENT = ("N",)
METHOD_SYMBOLS = "m:"
DEREFERENCE = "y:"


def origin(value):
    """The symbol a value derives from, through a fill, a mask and any dereference of it, or None."""
    value = value.value if isinstance(value, Fill) else value
    value = value.sym if isinstance(value, Masked) else value
    if not isinstance(value, Sym):
        return None
    sid = value.sid
    while sid.startswith(DEREFERENCE):
        sid = sid[len(DEREFERENCE):]
    return sid


def method_derived(value):
    """True for a value that is the result of the user method: a symbol of the method-result namespace."""
    value = value.value if isinstance(value, Fill) else value
    return all(derived(item) for item, _ in alternatives(value))


def derived(item):
    root = origin(item)
    return root is not None and root.startswith(METHOD_SYMBOLS)


def known(value):
    return not isinstance(value, Unknown)


def alternatives(value):
    """The (value, conditions) pairs a value stands for."""
    return value.items if isinstance(value, Alt) else ((value, ()),)


class Region:
    """The cells of one region. ``base`` is what an unwritten location reads: 0 for zeroed memory, ANYV for memory
    nothing initialized, SYMBOLIC for a region standing for memory the extraction does not know."""

    __slots__ = ("cells", "base", "owner", "_fp", "kind")

    def __init__(self, base=ANYV, cells=None, owner=None, kind=None):
        self.cells, self.base, self.owner, self._fp = cells if cells is not None else {}, base, owner, None
        self.kind = kind

    def copy(self, owner):
        return Region(self.base, dict(self.cells), owner, self.kind)

    def fingerprint(self):
        if self._fp is None:
            self._fp = (self.base, frozenset(self.cells.items()))
        return self._fp

    def fill_above(self, path):
        """The nearest Fill at or above a path, or None."""
        for size in range(len(path), -1, -1):
            cell = self.cells.get(path[:size])
            if isinstance(cell, Fill):
                return cell
            if isinstance(cell, int) and cell == 0:
                return ZERO
            if cell is not None:
                return None
        return None

    def read(self, path):
        cells = self.cells
        cell = cells.get(path)
        if cell is not None and not isinstance(cell, Fill):
            return cell
        fill = cell if cell is not None else self.fill_above(path)
        children = {p[len(path):]: v for p, v in cells.items() if p[:len(path)] == path and len(p) > len(path)}
        if children:
            return Agg(self.tree_of(fill, children))
        return fill.value if fill is not None else self.base

    @staticmethod
    def tree_of(fill, children):
        tree = dict(children)
        if fill is not None:
            tree[()] = fill
        return tree

    def tree(self, path):
        """Every cell below a path, relative, with the Fill covering them."""
        fill = self.fill_above(path)
        children = {p[len(path):]: v for p, v in self.cells.items() if p[:len(path)] == path}
        return self.tree_of(fill, children) if (children or fill is not None) else {(): Fill(self.base)}

    def clear_below(self, path):
        for p in [p for p in self.cells if p[:len(path)] == path and len(p) > len(path)]:
            del self.cells[p]


FINGERPRINTS = {}


class State:
    """One abstract machine state: the regions, what the path has established about symbols, and the events."""

    def __init__(self, world):
        self.world, self.mem, self.token = world, {}, object()
        self.prints, self.base = {}, {}
        self.facts, self.tags, self.events, self.flags = {}, frozenset(), (), frozenset()
        self.serial, self.watch = 0, frozenset()

    def fork(self):
        other = State(self.world)
        other.mem, other.facts, other.tags = dict(self.mem), dict(self.facts), self.tags
        other.prints, other.base = dict(self.prints), self.base
        other.events, other.flags, other.serial = self.events, self.flags, self.serial
        other.watch = self.watch
        self.token = object()
        return other

    def put(self, rid, region):
        """Make a region the content of an identifier."""
        self.mem[rid] = region
        self.prints.pop(rid, None)
        return region

    def region(self, rid):
        region = self.mem.get(rid)
        if region is None:
            region = self.base.get(rid) or self.world.initial(rid)
            if region is not None:
                self.put(rid, region)
        return region

    def freeze(self):
        """Move every region into the shared base: forks of this state copy only the regions written after."""
        self.base = {**self.base, **self.mem}
        self.mem, self.prints, self.token = {}, {}, object()

    def writable(self, rid):
        region = self.region(rid)
        if region is None:
            region = self.put(rid, Region(self.world.base_of(rid), owner=self.token))
        elif region.owner is not self.token:
            region = self.put(rid, region.copy(self.token))
        region._fp = None
        self.prints.pop(rid, None)
        return region

    def read(self, rid, path):
        region = self.region(rid)
        if region is None:
            return ANYV
        value = region.read(path)
        if value is SYMBOLIC:
            return Sym(f"{rid}/{'.'.join(map(str, path))}")
        if isinstance(value, Havoc):
            return Sym(f"{rid}/{'.'.join(map(str, path))}#{value.serial}")
        return value

    def tree(self, rid, path):
        region = self.region(rid)
        return {(): Fill(ANYV)} if region is None else region.tree(path)

    def note(self, rid, values):
        """A watched region received a value the user method did not produce: native work, event N."""
        if rid in self.watch and not all(method_derived(v) for v in values):
            if not self.events or self.events[-1] != NATIVE_EVENT:
                self.events = self.events + (NATIVE_EVENT,)

    def write(self, rid, path, value):
        if isinstance(value, Alt) and any(isinstance(item, Agg) for item, _ in value.items):
            regions = [Region(ANYV, dict(item) if isinstance(item, Agg) else {(): Fill(item)})
                       for item, _ in value.items]
            guards = [conditions for _, conditions in value.items]
            value = Agg(join_regions(regions, guards, self.token).tree(()))
        if isinstance(value, Agg):
            self.write_tree(rid, path, value)
            return
        self.note(rid, (value,))
        region = self.writable(rid)
        region.clear_below(path)
        region.cells[path] = value

    def write_tree(self, rid, path, tree):
        self.note(rid, tree.values())
        region = self.writable(rid)
        for p in [p for p in region.cells if p[:len(path)] == path]:
            del region.cells[p]
        for relative, value in tree.items():
            region.cells[path + relative] = value

    def havoc(self, rid, path):
        """Mark every location below a path as written by unread code."""
        self.serial += 1
        self.write(rid, path, Fill(Havoc(self.serial)))

    def drop(self, rid):
        self.mem.pop(rid, None)
        self.prints.pop(rid, None)

    def allocate(self, base=ANYV, kind=None):
        self.serial += 1
        rid = f"h:{self.serial}"
        self.put(rid, Region(base, owner=self.token, kind=kind))
        return rid

    def key(self, ignore=()):
        prints = self.prints
        for rid, region in self.mem.items():
            if rid not in prints:
                prints[rid] = FINGERPRINTS.setdefault(region.fingerprint(), len(FINGERPRINTS))
        regions = frozenset(prints.items()) if not ignore else frozenset(
            (rid, fp) for rid, fp in prints.items() if rid not in ignore)
        return regions, self.events, self.flags, frozenset(self.facts.items())


def join_states(states):
    """One state covering all of them: a location the states disagree on becomes an Alt of the values, each tagged
    with the source conditions its state holds beyond those every state holds."""
    common = frozenset.intersection(*(s.tags for s in states))
    result = states[0].fork()
    own = [s.tags - common for s in states]
    for rid in differing_regions(states):
        present = [(s.region(rid), tags) for s, tags in zip(states, own) if s.region(rid) is not None]
        result.put(rid, join_regions([r for r, _ in present], [t for _, t in present], result.token))
    result.facts = {k: v for k, v in states[0].facts.items() if all(s.facts.get(k) == v for s in states[1:])}
    result.tags, result.serial = common, max(s.serial for s in states)
    result.flags = frozenset().union(*(s.flags for s in states))
    result.events = tuple(dict.fromkeys(e for s in states for e in s.events))
    return result


def differing_regions(states):
    """The regions that are not one shared object in every state."""
    first = states[0].mem.items()
    return {rid for s in states[1:] for rid, _ in first ^ s.mem.items()}


def join_regions(regions, own, token):
    first = regions[0]
    if all(r.fingerprint() == first.fingerprint() for r in regions):
        return first
    base = first.base if all(r.base == first.base for r in regions) else ANYV
    joined = Region(base, owner=token, kind=first.kind)
    for path in {p for r in regions for p in r.cells}:
        joined.cells[path] = join_cells([cell_at(r, path) for r in regions], own)
    return joined


def cell_at(region, path):
    if path in region.cells:
        return region.cells[path]
    fill = region.fill_above(path)
    return fill.value if fill is not None else region.base


def join_cells(values, own):
    if all(v == values[0] for v in values):
        return values[0]
    fills = [isinstance(v, Fill) for v in values]
    if all(fills):
        return Fill(join_values([v.value for v in values], own))
    if any(fills):
        return ANYV
    return join_values(values, own)


def join_values(values, own):
    items = {}
    for value, tags in zip(values, own):
        for plain, conditions in alternatives(value):
            items[plain, tuple(sorted(set(conditions) | set(tags)))] = None
    if len(items) > ALT_CAP:
        return ANYV
    return Alt(tuple(items))
