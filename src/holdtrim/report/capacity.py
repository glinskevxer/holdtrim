"""How full the aeroplanes are, and how much more would have gone on.

Underload is the number the commercial side asks for and it is easy to get
wrong, because there are three limits and the one that binds changes with the
fuel. A short sector on light fuel is limited by the zero fuel weight and the
same aeroplane on a long one is limited at takeoff, so quoting one figure all
day is quoting the wrong one half the time.

Position utilisation is here as well, and it is a different question. A flight
can be full by weight with half its positions empty, or out of positions with
tonnes of payload left, and the fix is different in each case.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from holdtrim.balance.limits import check
from holdtrim.office import FlightFile, Office
from holdtrim.store import flights


@dataclass(frozen=True)
class Capacity:
    """One flight's fullness, by weight and by position."""

    flight_key: str
    reference: str
    registration: str
    route: str
    payload: int
    underload: int
    limited_by: str
    positions_used: int
    positions_total: int
    findings: int

    @property
    def positions_free(self) -> int:
        """Positions with nothing planned in them."""
        return self.positions_total - self.positions_used

    @property
    def offered(self) -> int:
        """What could have been carried if nothing else changed."""
        return self.payload + self.underload

    @property
    def weight_utilisation(self) -> Decimal:
        """Payload as a percentage of what the limits would have allowed."""
        if self.offered <= 0:
            return Decimal("0.0")
        return (Decimal(self.payload) * 100 / Decimal(self.offered)).quantize(Decimal("0.1"))

    @property
    def position_utilisation(self) -> Decimal:
        """Positions used as a percentage of the positions there are."""
        if self.positions_total <= 0:
            return Decimal("0.0")
        return (Decimal(self.positions_used) * 100 / Decimal(self.positions_total)).quantize(
            Decimal("0.1")
        )

    @property
    def full_by_weight(self) -> bool:
        """Whether the weight limits are what stopped more going on."""
        return self.underload <= 0

    @property
    def full_by_position(self) -> bool:
        """Whether every position is used."""
        return self.positions_free == 0

    def describe(self) -> str:
        """One line for the capacity report."""
        return (
            f"{self.reference} {self.route} {self.payload} kg, "
            f"{self.underload} kg spare, limited by {self.limited_by}, "
            f"{self.positions_used}/{self.positions_total} positions"
        )


def for_flight(file: FlightFile) -> Capacity:
    """Read one flight's capacity off its file."""
    figures = file.balance()
    return Capacity(
        flight_key=file.key,
        reference=file.sector.reference,
        registration=file.sector.registration,
        route=file.sector.route,
        payload=figures.payload,
        underload=figures.underload,
        limited_by=figures.limiting_weight,
        positions_used=len(file.plan.assignments),
        positions_total=len(file.kind.layout.positions),
        findings=len(check(figures)),
    )


def programme(connection: sqlite3.Connection, day: date) -> tuple[Capacity, ...]:
    """Every flight on a day, in the order the programme runs."""
    office = Office(connection=connection)
    return tuple(
        for_flight(office.flight(sector.key)) for sector in flights.on_day(connection, day)
    )


def carried(report: tuple[Capacity, ...]) -> int:
    """Everything carried across a set of flights."""
    return sum(entry.payload for entry in report)


def spare(report: tuple[Capacity, ...]) -> int:
    """Everything that could still have gone."""
    return sum(entry.underload for entry in report)


def limits_biting(report: tuple[Capacity, ...]) -> dict[str, int]:
    """How often each of the three weights was the binding one."""
    counted: dict[str, int] = {}
    for entry in report:
        counted[entry.limited_by] = counted.get(entry.limited_by, 0) + 1
    return dict(sorted(counted.items()))
