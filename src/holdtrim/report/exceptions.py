"""Everything wrong across a day, in one list.

A duty manager does not want to open eleven flights to find the two with
something wrong. This runs the checks that already exist over every flight on a
day and prints what they say, worst first.

Nothing new is checked here. If a rule is worth having it lives with the thing
it is about, and this report is the place they are read together.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from holdtrim.findings import Finding, stopping, watching
from holdtrim.model.flight import CANCELLED, DEPARTED
from holdtrim.office import Office, departure_checks
from holdtrim.store import flights


@dataclass(frozen=True)
class Against:
    """One flight and what was found against it."""

    reference: str
    key: str
    findings: tuple[Finding, ...]

    @property
    def stops(self) -> int:
        """How many of them stop the flight."""
        return len(stopping(self.findings))

    @property
    def notes(self) -> int:
        """How many are worth knowing and do not stop anything."""
        return len(watching(self.findings))

    @property
    def clean(self) -> bool:
        """Whether nothing at all was found."""
        return not self.findings

    def lines(self) -> tuple[str, ...]:
        """The flight and its findings, one a line."""
        return (
            f"{self.reference} {self.stops} stopping, {self.notes} note(s)",
            *(f"  {finding.severity} {finding.describe()}" for finding in self.findings),
        )


GONE = (DEPARTED, CANCELLED)


def outstanding(connection: sqlite3.Connection, day: date) -> tuple[str, ...]:
    """The flights on a day that anybody can still do anything about.

    A flight that has gone is not outstanding, whatever is wrong with it. It
    used to be on this list and it made the report exit non zero every night
    after the last departure, which is the fastest way to teach a shift to stop
    reading a report.
    """
    return tuple(
        sector.key for sector in flights.on_day(connection, day) if sector.status not in GONE
    )


def against(connection: sqlite3.Connection, day: date) -> tuple[Against, ...]:
    """Every flight on a day that has anything against it, worst first."""
    office = Office(connection=connection)
    found = []
    for sector in flights.on_day(connection, day):
        if sector.status in GONE:
            continue
        file = office.flight(sector.key)
        findings = departure_checks(connection, file)
        if findings:
            found.append(Against(reference=sector.reference, key=sector.key, findings=findings))
    return tuple(sorted(found, key=lambda entry: (-entry.stops, -entry.notes, entry.reference)))


def worst_first(report: tuple[Against, ...]) -> tuple[str, ...]:
    """The whole report as lines."""
    if not report:
        return ("nothing is outstanding",)
    printed: list[str] = []
    for entry in report:
        printed.extend(entry.lines())
    printed.append(
        f"{sum(entry.stops for entry in report)} stopping across {len(report)} flight(s)"
    )
    return tuple(printed)


def blocked(report: tuple[Against, ...]) -> tuple[str, ...]:
    """The flights that cannot go as they stand."""
    return tuple(entry.reference for entry in report if entry.stops)
