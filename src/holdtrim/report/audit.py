"""Everything the book holds about one flight, in one place.

This is the report that gets printed when somebody asks a question about a
flight that left weeks ago: an auditor, a claims department, or the office
itself trying to work out why a pallet is at the wrong station. It gathers what
is scattered across six tables and prints it in the order the shift happened.

Nothing here is computed fresh where a record exists. The issued loadsheet
figures come off the record of what was issued rather than off the plan, and
the two are printed together on purpose, because when they disagree that is the
answer to the question.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from holdtrim.balance.limits import check
from holdtrim.office import FlightFile, Office
from holdtrim.store import movements, sheets
from holdtrim.store.sheets import Issued

WIDTH = 74
RULE = "-" * WIDTH


@dataclass(frozen=True)
class Trail:
    """One flight, and everything recorded against it."""

    file: FlightFile
    issued: tuple[Issued, ...]
    moved: tuple[str, ...]

    @property
    def key(self) -> str:
        """The flight this trail is about."""
        return self.file.key

    @property
    def signed(self) -> bool:
        """Whether a loadsheet was ever issued for it."""
        return bool(self.issued)

    @property
    def editions(self) -> int:
        """How many times the sheet was issued."""
        return len(self.issued)

    @property
    def disagrees(self) -> bool:
        """Whether the plan now and the last issued sheet say different things."""
        if not self.issued:
            return False
        return self.issued[-1].payload != self.file.plan.payload


def gather(connection: sqlite3.Connection, flight_key: str) -> Trail:
    """Read everything the book holds about a flight."""
    file = Office(connection=connection).flight(flight_key)
    moved = tuple(entry.describe() for entry in movements.for_flight(connection, flight_key))
    return Trail(file=file, issued=tuple(sheets.editions(connection, flight_key)), moved=moved)


def lines(trail: Trail) -> list[str]:
    """The whole trail, printed in the order the shift happened."""
    file = trail.file
    sector = file.sector
    printed = [
        f"FLIGHT FILE {file.key}".center(WIDTH),
        RULE,
        f"aircraft {sector.registration} {file.kind.code}, crew {sector.crew}",
        f"route {sector.origin} to {sector.destination} on {sector.day.isoformat()}",
        f"status {sector.status}",
        f"dry operating weight {file.tail.dry_operating_weight} kg "
        f"index {file.tail.dry_operating_index}",
        f"weighed {file.tail.weighed_on.isoformat()}, "
        f"expires {file.tail.weighing_expires.isoformat()}",
        f"fuel takeoff {sector.takeoff_fuel} trip {sector.trip_fuel} taxi {sector.taxi_fuel}",
        RULE,
        "PLAN AS IT STANDS",
    ]
    if file.plan.empty:
        printed.append("nothing is planned")
    else:
        printed.extend(assignment.describe() for assignment in file.plan.assignments)
        printed.append(
            f"payload {file.plan.payload} kg over {len(file.plan.assignments)} position(s)"
        )
    findings = check(file.balance())
    printed.append(RULE)
    printed.append("CHECKS")
    printed.extend(finding.describe() for finding in findings)
    if not findings:
        printed.append("every check passes")
    printed.append(RULE)
    printed.append("LOADSHEETS ISSUED")
    if not trail.issued:
        printed.append("none")
    else:
        printed.extend(entry.describe() for entry in trail.issued)
        if trail.disagrees:
            printed.append(
                f"the plan now carries {file.plan.payload} kg and the last sheet "
                f"said {trail.issued[-1].payload} kg"
            )
    printed.append(RULE)
    printed.append("DEVICE MOVEMENTS ON THIS FLIGHT")
    printed.extend(trail.moved or ("none",))
    printed.append(RULE)
    return printed


def render(trail: Trail) -> str:
    """The trail as one block of text."""
    return "\n".join(lines(trail)) + "\n"
