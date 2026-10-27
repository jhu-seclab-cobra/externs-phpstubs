"""The shared C reader of the php-src producers (design-extraction-handlers.md).

``source`` reads one file, ``macros`` expands function-defining macros, ``definitions`` finds function definitions and
their call sites, ``registrations`` reads class registrations, builtin entries and linkage into a ``Program``.
Imports ``php_src`` only; no producer imports into it.
"""

from php_src_c.registrations import Program, Registration
from php_src_c.source import Source

__all__ = ["Program", "Registration", "Source"]
