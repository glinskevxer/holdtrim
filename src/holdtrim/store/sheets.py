"""The loadsheets that were issued, kept as figures rather than as paper.

An issued loadsheet is a statement somebody signed, so it is recorded rather
than regenerated. Regenerating it later would use whatever the book says now,
and the whole point of the record is to say what the book said then.

Only the figures are kept, not the printed page. The page can be laid out again
from the figures, and a stored page is a stored copy of a layout that will
change.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from holdtrim.errors import DuplicateError, NotFoundError, StateError
from holdtrim.sheet.loadsheet import Loadsheet
from holdtrim.store.flights import exists as flight_exists
from holdtrim.store.sqlite import one, rows, scalar_int, transaction

COLUMNS = (
    "flight_key, edition, issued_on, prepared_by, payload, zero_fuel_weight, "
    "takeoff_weight, landing_weight, underload, limited_by, takeoff_index, "
    "takeoff_percent_mac, trim_setting, lmc_weight"
)


@dataclass(frozen=True)
class Issued:
    """One edition of a loadsheet as it was signed for."""

    flight_key: str
    edition: int
    issued_on: date
    prepared_by: str
    payload: int
    zero_fuel_weight: int
    takeoff_weight: int
    landing_weight: int
    underload: int
    limited_by: str
    takeoff_index: Decimal
    takeoff_percent_mac: Decimal
    trim_setting: Decimal
    lmc_weight: int = 0

    def describe(self) -> str:
        """One line for the audit trail."""
        return (
            f"{self.flight_key} edition {self.edition} issued {self.issued_on.isoformat()} "
            f"by {self.prepared_by}, ZFW {self.zero_fuel_weight}, trim {self.trim_setting}"
        )


def _issued(row: sqlite3.Row) -> Issued:
    return Issued(
        flight_key=str(row["flight_key"]),
        edition=int(row["edition"]),
        issued_on=date.fromisoformat(str(row["issued_on"])),
        prepared_by=str(row["prepared_by"]),
        payload=int(row["payload"]),
        zero_fuel_weight=int(row["zero_fuel_weight"]),
        takeoff_weight=int(row["takeoff_weight"]),
        landing_weight=int(row["landing_weight"]),
        underload=int(row["underload"]),
        limited_by=str(row["limited_by"]),
        takeoff_index=Decimal(str(row["takeoff_index"])),
        takeoff_percent_mac=Decimal(str(row["takeoff_percent_mac"])),
        trim_setting=Decimal(str(row["trim_setting"])),
        lmc_weight=int(row["lmc_weight"]),
    )


def from_sheet(sheet: Loadsheet, on: date) -> Issued:
    """Take the figures off a loadsheet the way they will be recorded."""
    figures = sheet.balance
    return Issued(
        flight_key=sheet.plan.flight_key,
        edition=sheet.edition,
        issued_on=on,
        prepared_by=sheet.prepared_by,
        payload=sheet.payload,
        zero_fuel_weight=figures.zero_fuel.weight,
        takeoff_weight=figures.takeoff.weight,
        landing_weight=figures.landing.weight,
        underload=sheet.underload,
        limited_by=sheet.limiting_weight,
        takeoff_index=figures.takeoff.index,
        takeoff_percent_mac=sheet.takeoff_percent_mac,
        trim_setting=sheet.trim_setting,
        lmc_weight=sheet.changes.total,
    )


def record(connection: sqlite3.Connection, issued: Issued) -> Issued:
    """Put an issued edition on the record."""
    if not flight_exists(connection, issued.flight_key):
        raise StateError(f"no flight {issued.flight_key} on file to issue a loadsheet for")
    if held(connection, issued.flight_key, issued.edition) is not None:
        raise DuplicateError(
            f"edition {issued.edition} of {issued.flight_key} has already been issued"
        )
    with transaction(connection):
        connection.execute(
            f"INSERT INTO loadsheet ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                issued.flight_key,
                issued.edition,
                issued.issued_on.isoformat(),
                issued.prepared_by,
                issued.payload,
                issued.zero_fuel_weight,
                issued.takeoff_weight,
                issued.landing_weight,
                issued.underload,
                issued.limited_by,
                str(issued.takeoff_index),
                str(issued.takeoff_percent_mac),
                str(issued.trim_setting),
                issued.lmc_weight,
            ),
        )
    return issued


def held(connection: sqlite3.Connection, flight_key: str, edition: int) -> Issued | None:
    """One edition, or nothing where it was never issued."""
    row = one(
        connection,
        f"SELECT {COLUMNS} FROM loadsheet WHERE flight_key = ? AND edition = ?",
        (flight_key, edition),
    )
    return None if row is None else _issued(row)


def editions(connection: sqlite3.Connection, flight_key: str) -> list[Issued]:
    """Every edition issued for a flight, first to last."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM loadsheet WHERE flight_key = ? ORDER BY edition",
        (flight_key,),
    )
    return [_issued(row) for row in found]


def latest(connection: sqlite3.Connection, flight_key: str) -> Issued:
    """The edition that stands."""
    issued = editions(connection, flight_key)
    if not issued:
        raise NotFoundError(f"no loadsheet has been issued for {flight_key}")
    return issued[-1]


def next_edition(connection: sqlite3.Connection, flight_key: str) -> int:
    """The edition number a new sheet would take."""
    return len(editions(connection, flight_key)) + 1


def issued_on(connection: sqlite3.Connection, day: date) -> list[Issued]:
    """Everything issued on one day."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM loadsheet WHERE issued_on = ? ORDER BY flight_key, edition",
        (day.isoformat(),),
    )
    return [_issued(row) for row in found]


def count(connection: sqlite3.Connection) -> int:
    """How many editions the book holds."""
    return scalar_int(connection, "SELECT count(*) FROM loadsheet")
