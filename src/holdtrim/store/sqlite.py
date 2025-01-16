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

PRAGMAS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA busy_timeout = 5000",
)


def connect(path: Path | str) -> sqlite3.Connection:
    """Open a connection with the pragmas this package assumes are on."""
    try:
        connection = sqlite3.connect(str(path), isolation_level=None)
    except sqlite3.Error as exc:  # pragma: no cover - depends on the filesystem
        raise BookError(f"cannot open the book at {path}: {exc}") from exc
    connection.row_factory = sqlite3.Row
    for pragma in PRAGMAS:
        connection.execute(pragma)
    return connection


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
    """One unit of work. Commit on the way out, roll back on the way up."""
    connection.execute("BEGIN")
    try:
        yield connection
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    connection.execute("COMMIT")


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
