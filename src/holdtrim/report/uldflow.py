"""Where the devices went.

A ULD fleet leaks in one direction. Devices go out full and come back when
somebody remembers, and the station that ends up holding forty of them is
rarely the station that ordered them. The movement log has all of it and
nobody reads a movement log.

This turns the log into the two things anybody asks for: what each station
gained and lost over a period, and which devices have not moved since before it
started.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from holdtrim.store import movements, ulds


@dataclass(frozen=True)
class Flow:
    """What one station gained and lost."""

    station: str
    arrived: int
    left: int

    @property
    def net(self) -> int:
        """What the station is up or down over the period."""
        return self.arrived - self.left

    @property
    def gaining(self) -> bool:
        """Whether devices are piling up here."""
        return self.net > 0

    def describe(self) -> str:
        """One line for the flow report."""
        return f"{self.station} in {self.arrived}, out {self.left}, net {self.net:+d}"


@dataclass(frozen=True)
class Idle:
    """One device that has not moved for a while."""

    uld: str
    station: str
    since: date
    days: int

    def describe(self) -> str:
        """One line for the idle listing."""
        return f"{self.uld} at {self.station} since {self.since.isoformat()}, {self.days} day(s)"


def flows(connection: sqlite3.Connection, start: date, end: date) -> tuple[Flow, ...]:
    """What every station gained and lost between two days."""
    counted: dict[str, list[int]] = {}
    for moved in movements.listing(connection):
        if not start <= moved.day <= end:
            continue
        held = counted.setdefault(moved.station, [0, 0])
        if moved.inbound:
            held[0] += 1
        else:
            held[1] += 1
    return tuple(
        Flow(station=station, arrived=arrived, left=left)
        for station, (arrived, left) in sorted(counted.items())
    )


def idle(connection: sqlite3.Connection, on: date, *, days: int = 14) -> tuple[Idle, ...]:
    """Every device that has been standing longer than a number of days."""
    found = []
    for device in ulds.listing(connection):
        if not device.at_station:
            continue
        code = device.code.formatted()
        arrivals = [
            moved
            for moved in movements.for_uld(connection, code)
            if moved.inbound and moved.day <= on
        ]
        if not arrivals:
            continue
        since = arrivals[-1].day
        standing = (on - since).days
        if standing >= days:
            found.append(Idle(uld=code, station=device.at_station, since=since, days=standing))
    return tuple(sorted(found, key=lambda entry: (-entry.days, entry.uld)))


def busiest(report: tuple[Flow, ...]) -> str:
    """The station that handled the most, empty where nothing moved."""
    if not report:
        return ""
    return max(report, key=lambda flow: (flow.arrived + flow.left, flow.station)).station


def piling_up(report: tuple[Flow, ...]) -> tuple[Flow, ...]:
    """The stations that gained more than they lost, most first."""
    return tuple(sorted((flow for flow in report if flow.gaining), key=lambda flow: -flow.net))
