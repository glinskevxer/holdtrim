"""Reading a book over for the things foreign keys cannot catch.

Sqlite will not let a plan point at a flight that is not there. It will happily
hold a movement for a device nobody registered, a handling code from a build
two versions ago, and a setting whose value stopped being a number when
somebody edited the file by hand.

None of those stop the tool working today, which is why they accumulate. The
doctor finds them, says which rows, and changes nothing.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from holdtrim.cargo import handling
from holdtrim.store import consignments, settings, ulds
from holdtrim.store.migrations import MIGRATIONS, current_version
from holdtrim.store.sqlite import broken_references, integrity, rows

INTEGRITY = "integrity"
REFERENCES = "references"
SCHEMA = "schema"
ORPHAN = "orphan"
CODES = "handling codes"
SETTINGS = "settings"


@dataclass(frozen=True)
class Complaint:
    """One thing wrong with a book."""

    about: str
    detail: str

    def describe(self) -> str:
        """One line for the doctor's report."""
        return f"{self.about}: {self.detail}"


def file_itself(connection: sqlite3.Connection) -> list[Complaint]:
    """What sqlite says about its own file."""
    found = [Complaint(about=INTEGRITY, detail=said) for said in integrity(connection)]
    found.extend(Complaint(about=REFERENCES, detail=said) for said in broken_references(connection))
    return found


def schema(connection: sqlite3.Connection) -> list[Complaint]:
    """Whether the book has run every migration this build knows."""
    behind = MIGRATIONS[-1].version - current_version(connection)
    if behind <= 0:
        return []
    return [
        Complaint(
            about=SCHEMA,
            detail=f"{behind} migration(s) have not been applied, run init",
        )
    ]


def orphan_movements(connection: sqlite3.Connection) -> list[Complaint]:
    """Movements for devices that are not on the register."""
    registered = {device.code.formatted() for device in ulds.listing(connection)}
    found = rows(connection, "SELECT DISTINCT uld FROM uld_movement ORDER BY uld")
    return [
        Complaint(
            about=ORPHAN,
            detail=f"{row['uld']} has movements logged and is not on the ULD register",
        )
        for row in found
        if str(row["uld"]) not in registered
    ]


def unknown_codes(connection: sqlite3.Connection) -> list[Complaint]:
    """Handling codes on file that this build does not know."""
    found = []
    for consignment in consignments.listing(connection):
        unknown = handling.unknown(consignment.handling)
        if unknown:
            found.append(
                Complaint(
                    about=CODES,
                    detail=f"waybill {consignment.awb} carries {', '.join(unknown)}",
                )
            )
    return found


def unreadable_settings(connection: sqlite3.Connection) -> list[Complaint]:
    """Settings whose stored value is not the kind of thing they hold."""
    found = []
    for setting, value, was_set in settings.listing(connection):
        if not was_set:
            continue
        try:
            setting.read(value)
        except Exception as exc:  # noqa: BLE001 - the reason is what is reported
            found.append(Complaint(about=SETTINGS, detail=f"{setting.name} {exc}"))
    return found


def examine(connection: sqlite3.Connection) -> tuple[Complaint, ...]:
    """Every complaint, in the order a reader wants them."""
    return (
        *file_itself(connection),
        *schema(connection),
        *orphan_movements(connection),
        *unknown_codes(connection),
        *unreadable_settings(connection),
    )


def sound(complaints: tuple[Complaint, ...]) -> bool:
    """Whether the book has nothing wrong with it."""
    return not complaints
