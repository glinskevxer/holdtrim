"""Looking after the book: sizes, statistics, and taking old flights out.

A book that is worked every night grows, and the parts that grow are the parts
nobody reads again: flights from two seasons ago and the movement log behind
them. Nothing here deletes anything without being told a date, and the prune
reports what it would take before it takes it, because a book is the record
somebody argues from and half a record is worse than a big one.

Vacuum and analyse are here because they are the two sqlite operations that
actually matter on a file this shape, and because a load controller should not
have to know that.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from holdtrim.errors import BookError
from holdtrim.store.sqlite import rows, scalar_int, table_names, transaction

DATED_TABLES = {
    "sector": "day",
    "uld_movement": "day",
    "loadsheet": "issued_on",
    "consignment": "ready_on",
}

PRUNE_STATEMENTS = {
    "loadsheet": "DELETE FROM loadsheet WHERE issued_on < ?",
    "uld_movement": "DELETE FROM uld_movement WHERE day < ?",
    "consignment": "DELETE FROM consignment WHERE ready_on < ?",
    "sector": "DELETE FROM sector WHERE day < ?",
}


@dataclass(frozen=True)
class Size:
    """How big one table is."""

    table: str
    rows: int

    def describe(self) -> str:
        """One line for the size report."""
        return f"{self.table} {self.rows} row(s)"


@dataclass(frozen=True)
class Pruned:
    """What a prune took, or would take."""

    table: str
    rows: int
    before: date

    def describe(self) -> str:
        """One line for the prune report."""
        return f"{self.table} {self.rows} row(s) before {self.before.isoformat()}"


def sizes(connection: sqlite3.Connection) -> tuple[Size, ...]:
    """Every table and how many rows it holds, biggest first."""
    found = [
        Size(table=name, rows=scalar_int(connection, f"SELECT count(*) FROM {name}"))
        for name in table_names(connection)
    ]
    return tuple(sorted(found, key=lambda size: (-size.rows, size.table)))


def file_size(path: Path) -> int:
    """How many bytes the book takes on disk."""
    if not path.exists():
        raise BookError(f"no book at {path}")
    return path.stat().st_size


def analyse(connection: sqlite3.Connection) -> None:
    """Let sqlite work out its own statistics, which the planner then uses."""
    connection.execute("ANALYZE")


def vacuum(connection: sqlite3.Connection) -> None:
    """Rewrite the file, giving back the space deleted rows left behind."""
    connection.execute("VACUUM")


def would_prune(connection: sqlite3.Connection, before: date) -> tuple[Pruned, ...]:
    """What a prune would take, without taking any of it."""
    present = set(table_names(connection))
    found = []
    for table, column in sorted(DATED_TABLES.items()):
        if table not in present:
            continue
        held = scalar_int(
            connection,
            f"SELECT count(*) FROM {table} WHERE {column} < ?",
            (before.isoformat(),),
        )
        if held:
            found.append(Pruned(table=table, rows=held, before=before))
    return tuple(found)


def prune(connection: sqlite3.Connection, before: date) -> tuple[Pruned, ...]:
    """Take everything older than a day out, flights last.

    The statements are written out one per table rather than built from the
    table name. It is longer and it means the SQL in this file can be found by
    searching for it, which is the point.
    """
    taken = would_prune(connection, before)
    order = list(PRUNE_STATEMENTS)
    with transaction(connection):
        for entry in sorted(taken, key=lambda pruned: order.index(pruned.table)):
            connection.execute(PRUNE_STATEMENTS[entry.table], (before.isoformat(),))
    return taken


def index_names(connection: sqlite3.Connection) -> list[str]:
    """Every index in the book, in name order."""
    found = rows(
        connection,
        "SELECT name FROM sqlite_master WHERE type = 'index' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name",
    )
    return [str(row["name"]) for row in found]
