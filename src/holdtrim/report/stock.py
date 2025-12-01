"""What is standing at a station, and what it is costing.

Two different records answer "how many pallets are at Liege" and they are
allowed to disagree. The register is what somebody last typed, and the movement
log is what actually crossed the boundary. When they disagree the log is
usually right and the register is usually stale, but not always, which is why
the report prints both rather than picking one.

Demurrage is the other half. A device left standing past its free days starts
costing the station money, and nobody finds that out from a register that only
says where things are.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from holdtrim.model.uld import DAMAGED, SERVICEABLE
from holdtrim.store import movements, ulds

DEFAULT_FREE_DAYS = 5
DEFAULT_DAILY_RATE = 6


@dataclass(frozen=True)
class StockLine:
    """One base size at one station, counted three ways."""

    base: str
    held: int
    serviceable: int
    damaged: int

    @property
    def unusable(self) -> int:
        """Devices that are there and cannot be loaded."""
        return self.held - self.serviceable

    def describe(self) -> str:
        """One line for the stock report."""
        return (
            f"{self.base} {self.held} held, {self.serviceable} serviceable, {self.damaged} damaged"
        )


@dataclass(frozen=True)
class Standing:
    """One device that has been at a station a while."""

    uld: str
    base: str
    since: date
    days: int
    free_days: int
    daily_rate: int

    @property
    def chargeable_days(self) -> int:
        """Days past the free period, never negative."""
        return max(0, self.days - self.free_days)

    @property
    def charge(self) -> int:
        """What is owed for those days."""
        return self.chargeable_days * self.daily_rate

    @property
    def chargeable(self) -> bool:
        """Whether anything is owed at all."""
        return self.charge > 0

    def describe(self) -> str:
        """One line for the demurrage report."""
        return (
            f"{self.uld} standing since {self.since.isoformat()} "
            f"{self.days} day(s), {self.chargeable_days} chargeable, {self.charge}"
        )


def at(connection: sqlite3.Connection, station: str) -> tuple[StockLine, ...]:
    """The register's view of a station, by base size."""
    held = ulds.at_station(connection, station)
    bases = sorted({device.base for device in held})
    lines = []
    for base in bases:
        of_base = [device for device in held if device.base == base]
        lines.append(
            StockLine(
                base=base,
                held=len(of_base),
                serviceable=len([d for d in of_base if d.condition == SERVICEABLE]),
                damaged=len([d for d in of_base if d.condition == DAMAGED]),
            )
        )
    return tuple(lines)


def disagreements(
    connection: sqlite3.Connection, station: str, on: date
) -> tuple[tuple[str, int, int], ...]:
    """Base sizes where the register and the movement log do not agree."""
    registered = {line.base: line.held for line in at(connection, station)}
    logged = movements.balance(connection, station, on)
    bases = sorted(set(registered) | set(logged))
    return tuple(
        (base, registered.get(base, 0), logged.get(base, 0))
        for base in bases
        if registered.get(base, 0) != logged.get(base, 0)
    )


def standing(
    connection: sqlite3.Connection,
    station: str,
    on: date,
    *,
    free_days: int = DEFAULT_FREE_DAYS,
    daily_rate: int = DEFAULT_DAILY_RATE,
) -> tuple[Standing, ...]:
    """Every device standing at a station, longest first."""
    found = []
    for device in ulds.at_station(connection, station):
        code = device.code.formatted()
        history = movements.for_uld(connection, code)
        arrivals = [moved for moved in history if moved.inbound and moved.day <= on]
        if not arrivals:
            continue
        since = arrivals[-1].day
        found.append(
            Standing(
                uld=code,
                base=device.base,
                since=since,
                days=(on - since).days,
                free_days=free_days,
                daily_rate=daily_rate,
            )
        )
    return tuple(sorted(found, key=lambda entry: (-entry.days, entry.uld)))


def owing(
    connection: sqlite3.Connection,
    station: str,
    on: date,
    *,
    free_days: int = DEFAULT_FREE_DAYS,
    daily_rate: int = DEFAULT_DAILY_RATE,
) -> int:
    """What a station owes for everything it is holding too long."""
    return sum(
        entry.charge
        for entry in standing(connection, station, on, free_days=free_days, daily_rate=daily_rate)
    )
