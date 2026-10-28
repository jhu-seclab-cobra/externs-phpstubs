"""Object creation stage of the handler extraction (spec-extraction-handlers.md step 3).

For each registered class the object creator runs on the registered state with the class entry as argument; the
handler table of the object it returns is read from the returned object. Writes of the handlers field outside a
creator are followed by the type of the object they write: an object of a struct type takes every table written for
that type, because the code that allocates the type is the code that gives the class its objects.
"""

from handler_memory import Fn, Ptr, alternatives
from handler_minit import FIELD_WRITE, Policy, is_primitive, pure_functions, reaching

CREATE_BUDGET = 300_000
OBJECTS_NEW = "zend_objects_new"
HANDLERS = "handlers"


class Table:
    """One handler table an object can have: the region it lives in, or None when no rule resolves it, and the
    source identity that names it."""

    def __init__(self, region, identity):
        self.region, self.identity = region, identity

    def key(self):
        return self.region or self.identity

    def __eq__(self, other):
        return isinstance(other, Table) and other.key() == self.key()

    def __hash__(self):
        return hash(self.key())

    def __repr__(self):
        return f"Table({self.key()})"


class Created:
    """The result of the creation stage for one class: the tables of its objects and the struct type the creator
    allocated."""

    def __init__(self, tables, kind, creators):
        self.tables, self.kind, self.creators = tables, kind, creators


def walk(node):
    """Every tuple node below a compiled expression, itself included."""
    if isinstance(node, tuple):
        yield node
        for child in node:
            yield from walk(child)
    elif isinstance(node, list):
        for child in node:
            yield from walk(child)


class Creation:
    """The creation stage over the frozen registration state."""

    def __init__(self, registered):
        self.registered, self.machine = registered, registered.machine
        self.index, self.program = registered.index, registered.program
        self.state = registered.state
        self.executed = set()
        writers = [d for d in registered.definitions if FIELD_WRITE.search(d.body) and not is_primitive(self.machine, d.name)]
        interpreted = reaching(registered.definitions, writers)
        interpreted |= pure_functions(self.machine, registered.definitions, interpreted)
        self.policy = Policy(interpreted, lambda definition, text: bool(FIELD_WRITE.search(text)))
        self.writers = writers

    def create(self, name):
        """The Created of one registered class (folded name)."""
        entry = Ptr("c:" + name, ())
        creator = self.state.read(entry.rid, ("create_object",))
        tables, kind, creators = [], None, []
        for value, _ in alternatives(creator):
            for table, allocated, definition in self.created(entry, value):
                tables.append(table)
                kind = kind or allocated
                creators.append(definition)
        return Created(list(dict.fromkeys(tables)), kind, creators)

    def created(self, entry, creator):
        """The (table, allocated type, creator definition) outcomes of one creator value."""
        definition = self.creator_definition(creator)
        if definition is None:
            return [(Table(None, self.registered_identity(entry)), None, None)]
        self.machine.policy, self.machine.sites = self.policy, self.executed
        exits, complete = self.machine.call(definition, [entry], self.state.fork(), CREATE_BUDGET)
        outcomes = []
        for value, state in exits:
            outcomes.extend(self.table_of(value, state, definition))
        if not complete or not exits:
            outcomes.append((Table(None, identity(definition)), None, definition))
        return outcomes

    def creator_definition(self, creator):
        if creator == 0:
            return self.program.functions[OBJECTS_NEW][0]
        if not isinstance(creator, Fn):
            return None
        found = [d for d in self.program.functions.get(creator.name, ())
                 if not d.is_macro and (creator.source is None or d.source.relative == creator.source)]
        return found[0] if found else None

    def registered_identity(self, entry):
        registration = self.program.registrations.get(entry.rid[2:])
        return f"{registration.source}:{registration.function}" if registration else entry.rid

    def table_of(self, value, state, definition):
        """The (table, kind, creator) outcomes of the object a creator returned."""
        if not isinstance(value, Ptr):
            return [] if value == 0 else [(Table(None, identity(definition)), None, definition)]
        kind = state.region(value.rid).kind if state.region(value.rid) else None
        slot = state.read(value.rid, value.path + (HANDLERS,))
        return [(self.table(item, definition), kind, definition) for item, _ in alternatives(slot)]

    def table(self, pointer, definition):
        if isinstance(pointer, Ptr) and pointer.path == () and pointer.rid in self.registered.world.declarations:
            return Table(pointer.rid, table_identity(self.registered.world.declarations[pointer.rid]))
        return Table(None, identity(definition))


def identity(definition):
    return f"{definition.source.relative}:{definition.name}"


def table_identity(declarations):
    """The source path and symbol of a table: the declaration that initializes it, else the first that defines it."""
    chosen = next((d for d in declarations if d.initializer is not None), None)
    chosen = chosen or next((d for d in declarations if not d.extern), declarations[0])
    return f"{chosen.source.relative}:{chosen.name}"
