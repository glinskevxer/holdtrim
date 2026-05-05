"""The numbers the operator sets, kept in the book rather than in the code.

Some figures in load control are not rules, they are policy. How much last
minute change goes in the box before a new sheet is issued, how many days a
station holds a device for free, what it is charged after that. Different
operators set them differently and the same operator changes them, so they
belong to the book and travel with it.

Everything else stays in the code. A limit off a certificate is not policy and
there is no setting for it, because a setting is a thing somebody can change
and nobody may change a certified weight from a command line.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from holdtrim.errors import DataError, NotFoundError
from holdtrim.store.sqlite import one, rows, scalar_int, transaction

WHOLE = "whole number"
TEXT = "text"


@dataclass(frozen=True)
class Setting:
    """One thing the operator may set, and what it means."""

    name: str
    kind: str
    default: str
    meaning: str

    def read(self, value: str) -> object:
        """Turn the stored text into the thing it stands for."""
        if self.kind == WHOLE:
            if not value.strip().lstrip("-").isdigit():
                raise DataError(f"{self.name} has to be a whole number, not {value!r}")
            return int(value)
        return value

    def describe(self, value: str) -> str:
        """One line for the settings listing."""
        return f"{self.name} {value} ({self.meaning})"


KNOWN: dict[str, Setting] = {
    setting.name: setting
    for setting in (
        Setting(
            name="lmc.tolerance",
            kind=WHOLE,
            default="500",
            meaning="kilograms of last minute change before a new loadsheet",
        ),
        Setting(
            name="demurrage.free_days",
            kind=WHOLE,
            default="5",
            meaning="days a station holds a device before it is charged",
        ),
        Setting(
            name="demurrage.daily_rate",
            kind=WHOLE,
            default="6",
            meaning="charge a day after the free days",
        ),
        Setting(
            name="office.station",
            kind=TEXT,
            default="",
            meaning="the station this office works",
        ),
        Setting(
            name="teletype.origin",
            kind=TEXT,
            default="",
            meaning="our own teletype address",
        ),
    )
}


def known(name: str) -> Setting:
    """The definition of one setting."""
    wanted = name.strip().lower()
    if wanted not in KNOWN:
        raise NotFoundError(f"there is no setting called {wanted}")
    return KNOWN[wanted]


def stored(connection: sqlite3.Connection, name: str) -> str | None:
    """The stored text, or nothing where it was never set."""
    row = one(connection, "SELECT value FROM setting WHERE name = ?", (known(name).name,))
    return None if row is None else str(row["value"])


def text(connection: sqlite3.Connection, name: str) -> str:
    """The setting as text, falling back to its default."""
    held = stored(connection, name)
    return known(name).default if held is None else held


def whole(connection: sqlite3.Connection, name: str) -> int:
    """The setting as a whole number, which is what most of them are."""
    setting = known(name)
    if setting.kind != WHOLE:
        raise DataError(f"{setting.name} is {setting.kind}, not a whole number")
    read = setting.read(text(connection, name))
    return int(str(read))


def put(connection: sqlite3.Connection, name: str, value: str) -> str:
    """Set one setting, refusing a value it cannot be."""
    setting = known(name)
    setting.read(value)
    with transaction(connection):
        connection.execute(
            "INSERT INTO setting (name, value) VALUES (?, ?) "
            "ON CONFLICT (name) DO UPDATE SET value = excluded.value",
            (setting.name, value),
        )
    return value


def clear(connection: sqlite3.Connection, name: str) -> None:
    """Put a setting back to its default."""
    setting = known(name)
    if stored(connection, setting.name) is None:
        raise NotFoundError(f"{setting.name} has never been set")
    with transaction(connection):
        connection.execute("DELETE FROM setting WHERE name = ?", (setting.name,))


def listing(connection: sqlite3.Connection) -> list[tuple[Setting, str, bool]]:
    """Every setting, its value, and whether that value was set or defaulted."""
    held = {
        str(row["name"]): str(row["value"])
        for row in rows(connection, "SELECT name, value FROM setting")
    }
    return [
        (setting, held.get(name, setting.default), name in held)
        for name, setting in sorted(KNOWN.items())
    ]


def count(connection: sqlite3.Connection) -> int:
    """How many settings have been set away from their default."""
    return scalar_int(connection, "SELECT count(*) FROM setting")
