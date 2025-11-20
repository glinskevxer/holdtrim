"""A device arriving at a station or leaving it.

The ULD register says where a device is now. This says how it got there, and
the two are not the same thing. A register that is only ever overwritten
answers "where is PMC12345" and cannot answer "when did it leave Liege", which
is the question that comes up when a station is billed for holding one too
long.

A movement is a fact about a day. It is never edited, only added to, because
the whole point of it is to be the record somebody argues from later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from holdtrim.errors import DataError
from holdtrim.ids import UldCode, parse_station, parse_uld

ARRIVED = "in"
LEFT = "out"
DIRECTIONS = (ARRIVED, LEFT)

EMPTY = "empty"
LOADED = "loaded"
DAMAGED = "damaged"
STATES = (EMPTY, LOADED, DAMAGED)


@dataclass(frozen=True, order=True)
class Movement:
    """One device crossing one station's boundary on one day."""

    day: date
    station: str
    uld: UldCode
    direction: str
    flight_key: str = ""
    state: str = EMPTY
    note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "station", parse_station(self.station))
        direction = self.direction.strip().lower()
        if direction not in DIRECTIONS:
            raise DataError(f"{direction} is not a direction a device moves in")
        object.__setattr__(self, "direction", direction)
        state = self.state.strip().lower()
        if state not in STATES:
            raise DataError(f"{state} is not a state a device is recorded in")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "note", self.note.strip())

    @property
    def base(self) -> str:
        """The base size, for counting stock by type."""
        return self.uld.type_code

    @property
    def inbound(self) -> bool:
        """Whether this movement put a device into the station's stock."""
        return self.direction == ARRIVED

    @property
    def effect(self) -> int:
        """What this does to the count at the station, plus or minus one."""
        return 1 if self.inbound else -1

    @property
    def on_a_flight(self) -> bool:
        """Whether the movement was on an aeroplane rather than on the ground."""
        return self.flight_key != ""

    def describe(self) -> str:
        """One line for the movement log."""
        how = self.flight_key if self.on_a_flight else "by road"
        note = f" {self.note}" if self.note else ""
        return (
            f"{self.day.isoformat()} {self.station} {self.direction} {self.uld} "
            f"{self.state} {how}{note}"
        )


def movement(
    day: date,
    station: str,
    uld: str,
    direction: str,
    *,
    flight_key: str = "",
    state: str = EMPTY,
    note: str = "",
) -> Movement:
    """Build a movement from a written ULD code, which is how one is read in."""
    return Movement(
        day=day,
        station=station,
        uld=parse_uld(uld),
        direction=direction,
        flight_key=flight_key,
        state=state,
        note=note,
    )
