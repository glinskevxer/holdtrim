"""The movement message.

MVT is how the rest of the network finds out the aeroplane has gone. It is
short, it is sent twice a sector, and everything downstream hangs off it: the
arrival station starts its clock, the crew rostering system closes the duty,
and the ULD control at the far end knows what is coming.

    MVT
    QH412/12.OY-JAF.BLL
    AD1815/1830 EA1930 LGG
    DL41/0025

The departure line is off blocks, then airborne, then the estimated arrival and
where. A delay line follows it when there was one, with the reason code and how
long. The codes are IATA delay codes and this build does not interpret them, it
carries them, because arguing about which code a delay was is a job for the
people who were there.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from holdtrim.errors import DataError
from holdtrim.ids import parse_station
from holdtrim.message.teletype import URGENT, Message
from holdtrim.model.flight import Sector

_CLOCK = re.compile(r"^([01]\d|2[0-3])[0-5]\d$")
_DELAY_CODE = re.compile(r"^[0-9A-Z]{2}$")


def clock(value: str) -> str:
    """A time of day as four digits, which is all a message carries."""
    cleaned = value.strip()
    if not _CLOCK.match(cleaned):
        raise DataError(f"{value!r} is not a time written as HHMM")
    return cleaned


def delay(code: str, minutes: int) -> tuple[str, int]:
    """One delay, as a code and how long it was."""
    cleaned = code.strip().upper()
    if not _DELAY_CODE.match(cleaned):
        raise DataError(f"{code!r} is not a two character delay code")
    if minutes <= 0:
        raise DataError(f"a delay of {minutes} minutes is not a delay")
    return cleaned, minutes


@dataclass(frozen=True)
class Departure:
    """What is reported when the aeroplane leaves."""

    off_blocks: str
    airborne: str
    estimated_arrival: str
    arrival_station: str
    delays: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "off_blocks", clock(self.off_blocks))
        object.__setattr__(self, "airborne", clock(self.airborne))
        object.__setattr__(self, "estimated_arrival", clock(self.estimated_arrival))
        object.__setattr__(self, "arrival_station", parse_station(self.arrival_station))
        object.__setattr__(
            self, "delays", tuple(delay(code, minutes) for code, minutes in self.delays)
        )

    @property
    def delayed_by(self) -> int:
        """How long the delays came to, in minutes."""
        return sum(minutes for _code, minutes in self.delays)

    def lines(self) -> tuple[str, ...]:
        """The departure line, and a delay line where there was one."""
        first = (
            f"AD{self.off_blocks}/{self.airborne} EA{self.estimated_arrival} {self.arrival_station}"
        )
        if not self.delays:
            return (first,)
        codes = " ".join(f"DL{code}/{minutes:04d}" for code, minutes in self.delays)
        return (first, codes)


@dataclass(frozen=True)
class Arrival:
    """What is reported when the aeroplane is on stand."""

    touchdown: str
    on_blocks: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "touchdown", clock(self.touchdown))
        object.__setattr__(self, "on_blocks", clock(self.on_blocks))

    def lines(self) -> tuple[str, ...]:
        """The arrival line."""
        return (f"AA{self.touchdown}/{self.on_blocks}",)


def body(sector: Sector, movement: Departure | Arrival, *, station: str) -> tuple[str, ...]:
    """Every line under the type."""
    where = parse_station(station)
    return (f"{sector.reference}.{sector.registration}.{where}", *movement.lines())


def build(
    sector: Sector,
    movement: Departure | Arrival,
    *,
    station: str,
    addresses: tuple[str, ...],
    origin: str,
    filed: str,
    priority: str = URGENT,
) -> Message:
    """The whole MVT, envelope and all."""
    return Message(
        kind="MVT",
        addresses=addresses,
        origin=origin,
        filed=filed,
        body=body(sector, movement, station=station),
        priority=priority,
    )
