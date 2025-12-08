"""Writing the book out as CSV.

Somebody always wants the figures in a spreadsheet. The alternative to writing
this is people opening the sqlite file with whatever is to hand, which is how a
book ends up with a column quietly retyped.

Every export is one file per table, written whole, with a header row that names
the columns as the book names them. Nothing is renamed on the way out and
nothing is formatted for presentation, because an export that is prettified is
an export nobody can compare against the book it came from.
"""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from holdtrim.errors import BookError
from holdtrim.store.sqlite import rows, table_names

SKIPPED = {"schema_migration", "sqlite_sequence"}


@dataclass(frozen=True)
class Written:
    """One file that was written, and how much went in it."""

    table: str
    path: Path
    written: int

    def describe(self) -> str:
        """One line for the export report."""
        return f"{self.table} {self.written} row(s) to {self.path.name}"


def exportable(connection: sqlite3.Connection) -> list[str]:
    """Every table worth writing out, in name order."""
    return [name for name in table_names(connection) if name not in SKIPPED]


def columns(connection: sqlite3.Connection, table: str) -> list[str]:
    """The column names of one table, in the order the book declares them."""
    found = rows(connection, f"PRAGMA table_info({table})")
    if not found:
        raise BookError(f"no table called {table} in this book")
    return [str(row["name"]) for row in found]


def table(connection: sqlite3.Connection, name: str, destination: Path) -> Written:
    """Write one table out."""
    heads = columns(connection, name)
    path = destination / f"{name}.csv"
    written = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(heads)
        for row in rows(connection, f"SELECT * FROM {name}"):
            writer.writerow([row[head] for head in heads])
            written += 1
    return Written(table=name, path=path, written=written)


def everything(connection: sqlite3.Connection, destination: Path) -> tuple[Written, ...]:
    """Write every table out into one directory."""
    if destination.exists() and not destination.is_dir():
        raise BookError(f"{destination} is not a directory")
    destination.mkdir(parents=True, exist_ok=True)
    return tuple(table(connection, name, destination) for name in exportable(connection))


def total(written: tuple[Written, ...]) -> int:
    """How many rows the whole export came to."""
    return sum(entry.written for entry in written)
