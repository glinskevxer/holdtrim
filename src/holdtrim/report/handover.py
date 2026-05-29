"""The sheet the outgoing shift hands to the incoming one.

Everything on it is something that will become somebody's problem in the next
few hours: a flight still open, a flight closed with no loadsheet against it, a
weighing about to run out, a device that started costing money today, cargo
that is ready and is not on anything.

None of it is new information. All of it is scattered across five reports that
nobody reads at the end of a night shift, which is the whole reason this
exists.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from holdtrim.model.flight import CLOSED, PLANNED
from holdtrim.report.stock import standing
from holdtrim.store import consignments, fleet, flights, plans, settings, sheets

WEIGHING_WARNING_DAYS = 45


@dataclass(frozen=True)
class Handover:
    """What the next shift is walking into."""

    day: date
    station: str
    open_flights: tuple[str, ...]
    unsigned: tuple[str, ...]
    unplanned: tuple[str, ...]
    weighings: tuple[str, ...]
    chargeable: tuple[str, ...]
    waiting: tuple[str, ...]

    @property
    def quiet(self) -> bool:
        """Whether there is nothing to hand over at all."""
        return not any(
            (
                self.open_flights,
                self.unsigned,
                self.unplanned,
                self.weighings,
                self.chargeable,
                self.waiting,
            )
        )

    def lines(self) -> tuple[str, ...]:
        """The sheet as it is printed."""
        printed = [f"HANDOVER {self.station} {self.day.isoformat()}"]
        sections = (
            ("flights still open", self.open_flights),
            ("closed with no loadsheet", self.unsigned),
            ("open with no plan", self.unplanned),
            ("weighings running out", self.weighings),
            ("devices now chargeable", self.chargeable),
            ("cargo ready and not loaded", self.waiting),
        )
        for heading, entries in sections:
            if entries:
                printed.append(f"{heading}:")
                printed.extend(f"  {entry}" for entry in entries)
        if self.quiet:
            printed.append("nothing to hand over")
        return tuple(printed)


def gather(connection: sqlite3.Connection, station: str, day: date) -> Handover:
    """Read the handover for one station on one day."""
    where = station.strip().upper()
    departures = flights.out_of(connection, where, day)
    open_flights = tuple(sector.reference for sector in departures if sector.status == PLANNED)
    unsigned = tuple(
        sector.reference
        for sector in departures
        if sector.status == CLOSED and not sheets.editions(connection, sector.key)
    )
    unplanned = tuple(
        sector.reference
        for sector in departures
        if sector.status == PLANNED and not plans.exists(connection, sector.key)
    )
    weighings = tuple(
        f"{aeroplane.registration} expires {aeroplane.weighing_expires.isoformat()}"
        for aeroplane in fleet.weighings_due(connection, day, within_days=WEIGHING_WARNING_DAYS)
    )
    free_days = settings.whole(connection, "demurrage.free_days")
    rate = settings.whole(connection, "demurrage.daily_rate")
    chargeable = tuple(
        entry.describe()
        for entry in standing(connection, where, day, free_days=free_days, daily_rate=rate)
        if entry.chargeable
    )
    waiting = tuple(
        f"{consignment.awb} {consignment.gross_weight} kg for {consignment.destination}"
        for sector in departures
        for consignment in consignments.ready_by(connection, sector.origin, sector.destination, day)
    )
    return Handover(
        day=day,
        station=where,
        open_flights=open_flights,
        unsigned=unsigned,
        unplanned=unplanned,
        weighings=weighings,
        chargeable=chargeable,
        waiting=tuple(sorted(set(waiting))),
    )


def render(handover: Handover) -> str:
    """The sheet as one block of text."""
    return "\n".join(handover.lines()) + "\n"
