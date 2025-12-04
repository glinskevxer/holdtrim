"""A unit load device: the box or the pallet the cargo actually flies in.

A ULD is part of the aeroplane when it is certified, which is why its tare
weight is on the loadsheet and why a damaged one may not be loaded. It is also
an asset that belongs to somebody, moves between stations, and gets billed for
when it sits too long at the wrong one.

Tare matters more than it looks. It is dead weight the aeroplane lifts and the
customer does not pay for, so a plan built on a guessed tare is a plan that is
wrong by a few hundred kilograms before anything is put in it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from holdtrim.errors import DataError
from holdtrim.ids import UldCode, parse_station, parse_uld
from holdtrim.units import to_kilos

SERVICEABLE = "serviceable"
DAMAGED = "damaged"
IN_REPAIR = "in repair"
CONDITIONS = (SERVICEABLE, DAMAGED, IN_REPAIR)

FLAT = "flat"
SLOPING = "sloping"
CONTOURS = (FLAT, SLOPING)


@dataclass(frozen=True)
class Uld:
    """One device, with the two weights that decide what may go in it."""

    code: UldCode
    tare: int
    max_gross: int
    at_station: str = ""
    condition: str = SERVICEABLE
    contour: str = FLAT

    def __post_init__(self) -> None:
        object.__setattr__(self, "tare", to_kilos(self.tare, what="tare"))
        object.__setattr__(self, "max_gross", to_kilos(self.max_gross, what="maximum gross"))
        if self.tare <= 0:
            raise DataError(f"{self.code} has no tare weight")
        if self.max_gross <= self.tare:
            raise DataError(f"{self.code} cannot hold anything, tare is at or over max gross")
        if self.at_station:
            object.__setattr__(self, "at_station", parse_station(self.at_station))
        condition = self.condition.strip().lower()
        if condition not in CONDITIONS:
            raise DataError(f"{self.code} is in no condition this build knows: {condition}")
        object.__setattr__(self, "condition", condition)
        contour = self.contour.strip().lower()
        if contour not in CONTOURS:
            raise DataError(f"{self.code} has no contour called {contour}")
        object.__setattr__(self, "contour", contour)

    @property
    def base(self) -> str:
        """The three letter type code a position is told to accept."""
        return self.code.type_code

    @property
    def payload_capacity(self) -> int:
        """The most that may be put in it, tare already taken off."""
        return self.max_gross - self.tare

    @property
    def loadable(self) -> bool:
        """Only a serviceable device may be built up."""
        return self.condition == SERVICEABLE

    @property
    def in_transit(self) -> bool:
        """A device with no station is somewhere between two of them."""
        return self.at_station == ""

    def gross_at(self, contents: int) -> int:
        """What the device weighs with that much in it."""
        if contents < 0:
            raise DataError(f"{self.code} cannot hold a negative weight")
        return self.tare + contents

    def over_gross_by(self, contents: int) -> int:
        """How far past the maximum gross a load would put it."""
        return max(0, self.gross_at(contents) - self.max_gross)

    def at(self, station: str) -> Uld:
        """The same device recorded at another station."""
        return replace(self, at_station=station)

    def describe(self) -> str:
        """One line for a stock listing."""
        where = self.at_station if self.at_station else "in transit"
        return f"{self.code} tare {self.tare} max {self.max_gross} {where} {self.condition}"


def uld(
    code: str,
    tare: int,
    max_gross: int,
    *,
    at_station: str = "",
    condition: str = SERVICEABLE,
    contour: str = FLAT,
) -> Uld:
    """Build a device from a written code, which is how one is read in."""
    parsed: UldCode = parse_uld(code)
    return Uld(
        code=parsed,
        tare=tare,
        max_gross=max_gross,
        at_station=at_station,
        condition=condition,
        contour=contour,
    )
