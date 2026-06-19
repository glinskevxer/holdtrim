"""Pulling one flight's whole picture out of the book.

Every command that does anything interesting needs the same four things: the
flight, the aeroplane, the type it is and the plan for it. Assembling those
four in each command is how they end up subtly different, with one of them
reading the tail's type and another trusting what the flight says. There is
one way to assemble them and this is it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date

from holdtrim.balance.limits import check
from holdtrim.balance.loading import Balance, LoadedPosition
from holdtrim.errors import StateError
from holdtrim.findings import STOP, WATCH, Finding
from holdtrim.model.aircraft import AircraftType
from holdtrim.model.flight import DEPARTED, PLANNED, Sector
from holdtrim.model.tail import Tail
from holdtrim.plan.lmc import Changes
from holdtrim.plan.loadplan import LoadPlan
from holdtrim.sheet.loadsheet import Loadsheet
from holdtrim.store import fleet, flights, plans, sheets


@dataclass(frozen=True)
class FlightFile:
    """One flight and everything that has to agree with it."""

    sector: Sector
    tail: Tail
    kind: AircraftType
    plan: LoadPlan

    @property
    def key(self) -> str:
        """The filing key the whole file hangs off."""
        return self.sector.key

    @property
    def loads(self) -> tuple[LoadedPosition, ...]:
        """The plan as positions and weights the balance can work with."""
        return tuple(
            LoadedPosition(
                position=self.kind.layout.position(assignment.position),
                weight=assignment.weight,
                label=assignment.uld,
            )
            for assignment in self.plan.assignments
        )

    def balance(self) -> Balance:
        """The figures for this flight as it stands."""
        return Balance(
            kind=self.kind,
            tail=self.tail,
            loads=self.loads,
            taxi_fuel=self.sector.taxi_fuel,
            trip_fuel=self.sector.trip_fuel,
            takeoff_fuel=self.sector.takeoff_fuel,
        )

    def loadsheet(
        self, prepared_by: str, *, changes: Changes | None = None, edition: int = 1
    ) -> Loadsheet:
        """The loadsheet for this flight as it stands."""
        return Loadsheet(
            sector=self.sector,
            tail=self.tail,
            kind=self.kind,
            plan=self.plan,
            balance=self.balance(),
            prepared_by=prepared_by,
            edition=edition,
            changes=changes if changes is not None else Changes(),
        )

    def check_flyable(self) -> None:
        """Refuse a flight the aeroplane cannot legally operate."""
        if not self.tail.loadable:
            raise StateError(f"{self.tail.registration} is {self.tail.status} and cannot be loaded")
        if not self.tail.weighing_current(self.sector.day):
            raise StateError(
                f"{self.tail.registration} was weighed on "
                f"{self.tail.weighed_on.isoformat()} and that expired on "
                f"{self.tail.weighing_expires.isoformat()}"
            )


DEPARTURE = "departure"


def departure_checks(connection: sqlite3.Connection, file: FlightFile) -> tuple[Finding, ...]:
    """Everything between a flight and being allowed to go.

    The load checks are run again here rather than trusted from when the sheet
    was issued, because a plan can be changed after issue and nothing stops
    somebody doing it. A sheet that no longer describes the aeroplane is the
    one thing on this list that has actually happened.
    """
    found = []
    if file.sector.status == DEPARTED:
        found.append(
            Finding(
                check=DEPARTURE,
                where=file.sector.reference,
                detail="has already gone",
            )
        )
    issued = sheets.editions(connection, file.key)
    if not issued:
        found.append(
            Finding(
                check=DEPARTURE,
                where=file.sector.reference,
                detail="has no loadsheet issued against it",
            )
        )
    elif issued[-1].payload != file.plan.payload:
        found.append(
            Finding(
                check=DEPARTURE,
                where=file.sector.reference,
                detail=(
                    f"was signed for {issued[-1].payload} kg and the plan now carries "
                    f"{file.plan.payload} kg"
                ),
            )
        )
    if file.sector.status == PLANNED:
        found.append(
            Finding(
                check=DEPARTURE,
                where=file.sector.reference,
                detail="is still open",
                severity=WATCH,
            )
        )
    if not file.tail.weighing_current(file.sector.day):
        found.append(
            Finding(
                check=DEPARTURE,
                where=file.tail.registration,
                detail=f"was weighed on {file.tail.weighed_on.isoformat()} and that has expired",
            )
        )
    found.extend(check(file.balance()))
    return tuple(found)


def may_depart(findings: tuple[Finding, ...]) -> bool:
    """Whether nothing found stops the aeroplane going."""
    return all(finding.severity != STOP for finding in findings)


@dataclass
class Office:
    """A book, and the flights read out of it."""

    connection: sqlite3.Connection
    cache: dict[str, FlightFile] = field(default_factory=dict)

    def flight(self, key: str) -> FlightFile:
        """One flight's whole file."""
        if key in self.cache:
            return self.cache[key]
        sector = flights.get(self.connection, key)
        tail = fleet.get_tail(self.connection, sector.registration)
        kind = fleet.get_type(self.connection, tail.type_code)
        plan = plans.get_or_start(self.connection, key)
        file = FlightFile(sector=sector, tail=tail, kind=kind, plan=plan)
        self.cache[key] = file
        return file

    def on(self, designator: str, day: date) -> FlightFile:
        """One flight by designator and day."""
        return self.flight(flights.key_for(designator, day))

    def forget(self, key: str) -> None:
        """Drop a flight from the cache after it has been written to."""
        self.cache.pop(key, None)


def read(connection: sqlite3.Connection, key: str) -> FlightFile:
    """One flight's file, with no cache in the way."""
    return Office(connection=connection).flight(key)
