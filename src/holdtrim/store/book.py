"""The book as a whole: open it, count it, check it, copy it.

Everything above the store layer takes a :class:`Book` rather than a raw
connection, so that the rules about which books may be written to live in one
place instead of in every command.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from holdtrim.errors import BookError
from holdtrim.store.migrations import (
    MIGRATIONS,
    ahead_of_this_build,
    apply,
    current_version,
)
from holdtrim.store.sqlite import (
    broken_references,
    connect,
    integrity,
    scalar_int,
    table_names,
)

COUNTED_TABLES = (
    "station",
    "aircraft_type",
    "tail",
    "consignment",
    "uld",
    "sector",
    "load_plan",
    "uld_movement",
    "dangerous_goods",
    "loadsheet",
)


@dataclass
class Book:
    """An open book and the file it came from."""

    path: Path
    connection: sqlite3.Connection

    @property
    def version(self) -> int:
        """The schema version this file has been migrated to."""
        return current_version(self.connection)

    def counts(self) -> dict[str, int]:
        """How many rows sit in each table worth counting."""
        present = set(table_names(self.connection))
        return {
            table: scalar_int(self.connection, f"SELECT count(*) FROM {table}")
            for table in COUNTED_TABLES
            if table in present
        }

    def verify(self) -> list[str]:
        """Everything wrong with the file, empty when it is sound."""
        problems = list(integrity(self.connection))
        problems.extend(broken_references(self.connection))
        behind = MIGRATIONS[-1].version - self.version
        if behind > 0:
            problems.append(f"{behind} migration(s) have not been applied to this book")
        return problems

    def backup(self, destination: Path) -> Path:
        """Copy the book somewhere safe, refusing to write over a file."""
        if destination.exists():
            raise BookError(f"{destination} is already there, not writing over it")
        with connect(destination) as target:
            self.connection.backup(target)
        target.close()
        return destination

    def close(self) -> None:
        """Let the handle go."""
        self.connection.close()


def initialise(path: Path) -> Path:
    """Create a book, or bring an existing one up to the current schema."""
    connection = connect(path)
    try:
        apply(connection)
    finally:
        connection.close()
    return path


@contextmanager
def open_book(path: Path, *, create: bool = False) -> Iterator[Book]:
    """Open a book that is ready to be written to, and close it after."""
    if not path.exists():
        if not create:
            raise BookError(f"no book at {path}, run init first")
        initialise(path)
    connection = connect(path)
    book = Book(path=path, connection=connection)
    try:
        ahead = ahead_of_this_build(connection)
        if ahead:
            raise BookError(
                f"the book at {path} was written by a newer holdtrim, "
                f"{ahead} schema version(s) ahead of this one"
            )
        if create:
            apply(connection)
        elif book.version < MIGRATIONS[-1].version:
            raise BookError(
                f"the book at {path} is at schema {book.version} "
                f"and this build needs {MIGRATIONS[-1].version}, run init"
            )
        yield book
    finally:
        book.close()


def copy_book(source: Path, destination: Path) -> Path:
    """Copy a closed book file, journal and all, without opening it."""
    if not source.exists():
        raise BookError(f"no book at {source}")
    if destination.exists():
        raise BookError(f"{destination} is already there, not writing over it")
    shutil.copyfile(source, destination)
    return destination
