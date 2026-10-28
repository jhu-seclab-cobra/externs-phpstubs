"""The world of the handler machine: the initial contents of the regions no rule has written yet."""

from handler_memory import ANYV, SYMBOLIC, Region, State
from handler_prims import EXCEPTION, EXCEPTIONS_REGION
from php_src_c.definitions import parse_expression


class GlobalFrame:
    """The scope of a file-scope initializer: only the file's own names resolve."""

    def __init__(self, source):
        self.source, self.vars, self.arrays, self.depth = source, {}, set(), 0


class World:
    """Region contents before any write: a file-scope handler table holds its initializer (zero when it has none),
    the exception flag is clear, and every other global or dereferenced unknown pointer holds symbols."""

    def __init__(self, index):
        self.index, self.machine = index, None
        self.declarations = {}
        for declarations in index.tables.values():
            for declaration in declarations:
                self.declarations.setdefault(declaration.region(), []).append(declaration)

    def initial(self, rid):
        if rid == EXCEPTIONS_REGION:
            return Region(SYMBOLIC, {EXCEPTION: 0})
        if rid in self.declarations:
            return self.table(self.declarations[rid])
        if rid[0] in "gy":
            return Region(SYMBOLIC)
        return None

    def base_of(self, rid):
        return ANYV

    def table(self, declarations):
        """The region of a table: the declaration with an initializer decides; none means static storage, zero."""
        region = Region(0)
        for declaration in declarations:
            if declaration.initializer is None:
                continue
            tree = self.evaluate(declaration)
            region.cells.update(tree)
            break
        return region

    def evaluate(self, declaration):
        text = self.index.pre.expand(declaration.initializer, declaration.source, self.index.disabled)
        node = parse_expression(text)
        frame, state = GlobalFrame(declaration.source), State(self)
        return self.machine.initializer(node, self.index.fields, state, frame)
