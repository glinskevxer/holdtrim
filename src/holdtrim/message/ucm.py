"""The ULD control message.

The ULD register at each station only stays right if every movement is
reported, and the UCM is how it is reported. It is the message that gets
forgotten, because nothing on the aeroplane depends on it and the aeroplane
goes anyway. Six weeks later somebody is looking for forty pallets.

    UCM
    QH412/12.OY-JAF.BLL
    -LGG
    OFF.PMC12345QH/L
    ON.AKE10001QH/E

Each device is reported with a state letter: L loaded, E empty, D damaged. A
device that goes off damaged is the station's problem to repair and the state
letter is how they find out, so it is not optional and there is no default.
"""

from __future__ import annotations

from dataclasses import dataclass

from holdtrim.errors import DataError
from holdtrim.ids import parse_station, parse_uld
from holdtrim.message.teletype import URGENT, Message
from holdtrim.model.flight import Sector
from holdtrim.model.uld import DAMAGED, Uld

ON = "ON"
OFF = "OFF"
DIRECTIONS = (ON, OFF)

LOADED = "L"
EMPTY = "E"
DAMAGED_STATE = "D"
STATES = (LOADED, EMPTY, DAMAGED_STATE)


@dataclass(frozen=True)
class DeviceMovement:
    """One device going on or coming off, and what state it is in."""

    uld: str
    direction: str
    state: str = EMPTY

    def __post_init__(self) -> None:
        object.__setattr__(self, "uld", parse_uld(self.uld).formatted())
        direction = self.direction.strip().upper()
        if direction not in DIRECTIONS:
            raise DataError(f"{direction} is not a direction a device moves in")
        object.__setattr__(self, "direction", direction)
        state = self.state.strip().upper()
        if state not in STATES:
            raise DataError(f"{state} is not a state a device is reported in")
        object.__setattr__(self, "state", state)

    @property
    def damaged(self) -> bool:
        """Whether the receiving station has a repair to arrange."""
        return self.state == DAMAGED_STATE

    def line(self) -> str:
        """The device as one line of the message."""
        return f"{self.direction}.{self.uld}/{self.state}"


def state_of(device: Uld, *, loaded: bool) -> str:
    """The state letter for a device, damage taking priority over anything else."""
    if device.condition == DAMAGED:
        return DAMAGED_STATE
    return LOADED if loaded else EMPTY


def body(sector: Sector, movements: tuple[DeviceMovement, ...], *, station: str) -> tuple[str, ...]:
    """Every line under the type."""
    where = parse_station(station)
    lines = [f"{sector.reference}.{sector.registration}.{where}", f"-{sector.destination}"]
    for direction in DIRECTIONS:
        for movement in movements:
            if movement.direction == direction:
                lines.append(movement.line())
    return tuple(lines)


def build(
    sector: Sector,
    movements: tuple[DeviceMovement, ...],
    *,
    station: str,
    addresses: tuple[str, ...],
    origin: str,
    filed: str,
    priority: str = URGENT,
) -> Message:
    """The whole UCM, envelope and all."""
    if not movements:
        raise DataError(f"there is nothing to report on {sector.reference}")
    return Message(
        kind="UCM",
        addresses=addresses,
        origin=origin,
        filed=filed,
        body=body(sector, movements, station=station),
        priority=priority,
    )
