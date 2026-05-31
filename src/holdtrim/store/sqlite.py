"""Opening the book, and closing it again.

A sqlite connection is a context manager for its transaction, not for itself.
Leaving a ``with connect(...)`` block commits and leaves the handle open, which
on 3.13 shows up much later as a ResourceWarning attributed to whichever test
the garbage collector happened to interrupt. Everything here goes through
:func:`opened`, which closes.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from holdtrim.errors import BookError

BUSY_TIMEOUT_MS = 5000
LOCKED = "database is locked"

PRAGMAS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
)


def connect(path: Path | str, *, busy_timeout: int = BUSY_TIMEOUT_MS) -> sqlite3.Connection:
    """Open a connection with the pragmas this package assumes are on.

    The busy timeout is how long sqlite waits for another writer before it
    gives up. Waiting is done inside sqlite rather than in a retry loop here,
    which keeps this package free of anything that sleeps and means the wait
    ends the moment the other writer commits.
    """
    try:
        connection = sqlite3.connect(str(path), isolation_level=None)
    except sqlite3.Error as exc:  # pragma: no cover - depends on the filesystem
        raise BookError(f"cannot open the book at {path}: {exc}") from exc
    connection.row_factory = sqlite3.Row
    for pragma in PRAGMAS:
        connection.execute(pragma)
    connection.execute(f"PRAGMA busy_timeout = {int(busy_timeout)}")
    return connection


def busy_timeout(connection: sqlite3.Connection) -> int:
    """How long this connection waits for another writer, in milliseconds."""
    return scalar_int(connection, "PRAGMA busy_timeout")


@contextmanager
def opened(path: Path | str) -> Iterator[sqlite3.Connection]:
    """Open, hand over, and close whatever happens."""
    connection = connect(path)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """One unit of work. Commit on the way out, roll back on the way up.

    The write lock is taken at the start rather than at the first write. A
    plain BEGIN is deferred, which means a second writer gets as far as running
    half its statements before finding out it cannot have the book, and the
    error then points at whichever statement happened to be first.

    A book held open by another writer for longer than the busy timeout comes
    back as a plain sqlite error that says nothing about what to do. It is
    turned into a book error here, because the person seeing it is a load
    controller and the thing they need to know is that somebody else has the
    book open.
    """
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        raise _locked(exc) from exc
    try:
        yield connection
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    try:
        connection.execute("COMMIT")
    except sqlite3.OperationalError as exc:  # pragma: no cover - needs a second writer
        connection.execute("ROLLBACK")
        raise _locked(exc) from exc


def _locked(exc: sqlite3.OperationalError) -> Exception:
    """Turn a lock into something worth reading, and leave anything else alone."""
    if LOCKED in str(exc):
        return BookError(
            "the book is open somewhere else and did not come free in time, "
            "close the other holdtrim and try again"
        )
    return exc


def one(
    connection: sqlite3.Connection, sql: str, parameters: tuple[object, ...] = ()
) -> sqlite3.Row | None:
    """The single row a lookup expects, or nothing."""
    cursor = connection.execute(sql, parameters)
    try:
        found: sqlite3.Row | None = cursor.fetchone()
    finally:
        cursor.close()
    return found


def rows(
    connection: sqlite3.Connection, sql: str, parameters: tuple[object, ...] = ()
) -> list[sqlite3.Row]:
    """Every row of a query, read out and the cursor closed."""
    cursor = connection.execute(sql, parameters)
    try:
        found: list[sqlite3.Row] = cursor.fetchall()
    finally:
        cursor.close()
    return found


def scalar(connection: sqlite3.Connection, sql: str, parameters: tuple[object, ...] = ()) -> object:
    """The first column of the first row, for counts and sums."""
    row = one(connection, sql, parameters)
    if row is None:
        raise BookError(f"no row came back for {sql!r}")
    return row[0]


def scalar_int(
    connection: sqlite3.Connection, sql: str, parameters: tuple[object, ...] = ()
) -> int:
    """A count or a sum, read as the integer the caller was going to make it."""
    value = scalar(connection, sql, parameters)
    if value is None:
        return 0
    if not isinstance(value, int):
        raise BookError(f"expected a whole number from {sql!r}, got {value!r}")
    return value


def table_names(connection: sqlite3.Connection) -> list[str]:
    """Every table in the book, in name order, sqlite's own excluded."""
    found = rows(
        connection,
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name",
    )
    return [str(row["name"]) for row in found]


def integrity(connection: sqlite3.Connection) -> list[str]:
    """Whatever sqlite says is wrong with the file, empty when it is fine."""
    reported = [str(row[0]) for row in rows(connection, "PRAGMA integrity_check")]
    if reported == ["ok"]:
        return []
    return reported


def broken_references(connection: sqlite3.Connection) -> list[str]:
    """Foreign keys pointing at rows that are not there any more."""
    found = rows(connection, "PRAGMA foreign_key_check")
    return [f"{row[0]} row {row[1]} references missing {row[2]}" for row in found]
