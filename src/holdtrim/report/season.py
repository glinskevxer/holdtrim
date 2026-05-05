"""A period, summed up.

The question at the end of a month is not what any one flight did, it is
whether the operation is carrying what it said it would and where the capacity
went. That needs the flights, the loadsheets that were issued against them, and
what the limits were doing, all over the same dates.

Averages are given as whole percentages and totals as kilograms. Nothing here
is a forecast: it is what happened, and the office has enough forecasts.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from holdtrim.errors import DataError
from holdtrim.report.capacity import Capacity, programme
from holdtrim.store import sheets


@dataclass(frozen=True)
class Period:
    """The dates a summary covers."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise DataError(
                f"a period cannot end on {self.end.isoformat()} and start on "
                f"{self.start.isoformat()}"
            )

    @property
    def days(self) -> int:
        """How many days it covers, both ends counted."""
        return (self.end - self.start).days + 1

    def dates(self) -> tuple[date, ...]:
        """Every day in the period."""
        return tuple(self.start + timedelta(days=offset) for offset in range(self.days))

    def describe(self) -> str:
        """One line for the heading."""
        return f"{self.start.isoformat()} to {self.end.isoformat()}, {self.days} day(s)"


@dataclass(frozen=True)
class Summary:
    """What a period came to."""

    period: Period
    flights: int
    carried: int
    spare: int
    findings: int
    issued: int
    limits: dict[str, int]

    @property
    def flown_days(self) -> int:
        """Days with at least one flight on them."""
        return (self.flights and self.period.days) or 0

    @property
    def average_payload(self) -> int:
        """What a flight carried on average, rounded down."""
        if not self.flights:
            return 0
        return self.carried // self.flights

    @property
    def utilisation(self) -> Decimal:
        """Payload as a percentage of what the limits would have allowed."""
        offered = self.carried + self.spare
        if offered <= 0:
            return Decimal("0.0")
        return (Decimal(self.carried) * 100 / Decimal(offered)).quantize(Decimal("0.1"))

    @property
    def binding(self) -> str:
        """The limit that bound most often, empty where nothing flew."""
        if not self.limits:
            return ""
        return max(self.limits, key=lambda name: (self.limits[name], name))

    def lines(self) -> tuple[str, ...]:
        """The summary as it is printed."""
        printed = [
            self.period.describe(),
            f"flights {self.flights}",
            f"carried {self.carried} kg",
            f"spare {self.spare} kg",
            f"average payload {self.average_payload} kg",
            f"utilisation {self.utilisation} percent",
            f"loadsheets issued {self.issued}",
            f"findings {self.findings}",
        ]
        for name, times in sorted(self.limits.items()):
            printed.append(f"limited by {name} on {times} flight(s)")
        return tuple(printed)


def flights_in(connection: sqlite3.Connection, period: Period) -> tuple[Capacity, ...]:
    """Every flight in the period, day by day."""
    found: list[Capacity] = []
    for day in period.dates():
        found.extend(programme(connection, day))
    return tuple(found)


def summarise(connection: sqlite3.Connection, period: Period) -> Summary:
    """Add a period up."""
    found = flights_in(connection, period)
    limits: dict[str, int] = {}
    for entry in found:
        limits[entry.limited_by] = limits.get(entry.limited_by, 0) + 1
    issued = sum(len(sheets.issued_on(connection, day)) for day in period.dates())
    return Summary(
        period=period,
        flights=len(found),
        carried=sum(entry.payload for entry in found),
        spare=sum(entry.underload for entry in found),
        findings=sum(entry.findings for entry in found),
        issued=issued,
        limits=limits,
    )
