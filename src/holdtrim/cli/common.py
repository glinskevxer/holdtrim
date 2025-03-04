"""Bits every command group needs: the book, the exit codes, and a table.

Exit codes matter here. This tool gets called from a shift handover script and
from the ramp's own tooling, and those callers branch on the status. A rule
refusal is not the same as a typo and neither is the same as a missing book.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import click

from holdtrim.errors import (
    BookError,
    DataError,
    DuplicateError,
    HoldtrimError,
    NotFoundError,
    RuleError,
    StateError,
)
from holdtrim.store.book import Book, open_book

DEFAULT_BOOK = Path("holdtrim.sqlite3")

EXIT_CODES: dict[type[HoldtrimError], int] = {
    DataError: 2,
    NotFoundError: 3,
    DuplicateError: 4,
    StateError: 5,
    RuleError: 6,
    BookError: 7,
}
UNKNOWN_ERROR_EXIT = 1


@dataclass
class Settings:
    """What every command needs before it starts."""

    book: Path


def exit_code_for(error: HoldtrimError) -> int:
    """The status a caller branches on, most specific class first."""
    for cls in type(error).__mro__:
        if issubclass(cls, HoldtrimError) and cls in EXIT_CODES:
            return EXIT_CODES[cls]
    return UNKNOWN_ERROR_EXIT


def settings(ctx: click.Context) -> Settings:
    """The settings the top level command put on the context."""
    return ctx.ensure_object(Settings)


@contextmanager
def opened_book(ctx: click.Context, *, create: bool = False) -> Iterator[Book]:
    """The book this invocation works on."""
    with open_book(settings(ctx).book, create=create) as book:
        yield book


def parse_day(value: str) -> date:
    """A day written the only way this tool accepts one."""
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise DataError(f"{value!r} is not a date written as YYYY-MM-DD") from None


def table(headers: Sequence[str], body: Sequence[Sequence[str]]) -> str:
    """A plain column layout, wide enough for the widest cell in each column."""
    if not body:
        return ""
    widths = [len(header) for header in headers]
    for row in body:
        for column, cell in enumerate(row):
            widths[column] = max(widths[column], len(cell))
    lines = ["  ".join(header.ljust(widths[i]) for i, header in enumerate(headers)).rstrip()]
    lines.append("  ".join("-" * width for width in widths).rstrip())
    for row in body:
        lines.append("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
    return "\n".join(lines)


def echo_table(headers: Sequence[str], body: Sequence[Sequence[str]], *, empty: str) -> None:
    """Print a table, or say plainly that there is nothing to print."""
    if not body:
        click.echo(empty)
        return
    click.echo(table(headers, body))
