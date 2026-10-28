"""Effective object-handler tables of one php-src checkout (design-extraction-handlers.md, spec-extraction-handlers.md).

The class registrations run as the engine runs them, each registered class's object creator runs to find the tables
its objects take, and the cast, compare and operation handlers of each table run once per consumed request to
summarize their normal results. A value no rule knows stays unknown: an unknown handler pointer is never a NULL slot
and an unproven summary is omitted.
"""

import php_src
from handler_create import Creation
from handler_minit import Registered
from handler_requests import consumed_requests
from handler_sites import Sites, typed_tables
from handler_summary import Summarizer
from handler_tables import Report, TableBuilder

OBJECT_CLASSIFIER = "class"


def effective_string_method(declarations, name):
    """True when the class or one of its parent classes declares a ``__toString`` method."""
    seen = set()
    while name in declarations and name not in seen:
        seen.add(name)
        if declarations[name].to_string:
            return True
        name = declarations[name].parent
    return False


def read_handler_tables(program, declarations):
    """The handler tables of each registered class that has objects: ``({folded class name: [Table]}, Report)``.

    A class gets the tables its creator's objects take and the tables written to the objects of the struct type its
    creator allocates. A class no stub declares, and a class that is an interface, a trait or an enum, has none."""
    registered = Registered(program)
    creation = Creation(registered)
    created = {name: creation.create(name) for name in registered.registered}
    report = Report()
    report.dispositions = Sites(registered, creation).classify()
    typed = typed_tables(report.dispositions)
    builder = TableBuilder(registered, Summarizer(registered), consumed_requests(program), report)
    classes = {}
    for name in sorted(created):
        declaration = declarations.get(name)
        if declaration is None or declaration.classifier != OBJECT_CLASSIFIER:
            continue
        tables = created[name].tables + typed.get(created[name].kind, [])
        if not tables:
            raise php_src.ExtractionFailure(f"{name}: no handler table reaches the objects of the class")
        has_method = effective_string_method(declarations, name)
        classes[name] = [found for table in dict.fromkeys(tables) for found in builder.tables(table, has_method)]
    return classes, report
