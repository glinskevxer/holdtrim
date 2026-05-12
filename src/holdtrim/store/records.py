"""The three things every store does the same way.

Seven modules under store each had their own exists, count and delete, and the
seven were the same code with a different table name in it. They are here now,
with the table names written out one per store rather than passed in, so that
the SQL a store runs can still be found by searching for the table.
"""

from __future__ import annotations

import sqlite3

from holdtrim.errors import NotFoundError
from holdtrim.store.sqlite import scalar_int, transaction


def held(connection: sqlite3.Connection, statement: str, key: object) -> bool:
    """Whether a counting statement finds anything for a key."""
    return scalar_int(connection, statement, (key,)) > 0


def counted(connection: sqlite3.Connection, statement: str) -> int:
    """How many rows a counting statement finds."""
    return scalar_int(connection, statement)


def dropped(
    connection: sqlite3.Connection,
    *,
    exists_statement: str,
    delete_statement: str,
    key: object,
    missing: str,
) -> None:
    """Delete one row by key, refusing when it is not there."""
    if not held(connection, exists_statement, key):
        raise NotFoundError(missing)
    with transaction(connection):
        connection.execute(delete_statement, (key,))
