"""A loading position, and what will and will not go in it.

A position is not just an arm and a weight limit. The floor underneath it has
a rating, and that rating is per metre of fuselage and per square metre of
floor, so the same 1500 kg is fine as a pallet and is not fine as a crate on
its edge. Both readings are here because both are on the loading manual page
and a load controller checks both.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from holdtrim.errors import DataError
from holdtrim.units import to_kilos, to_metres

MAIN_DECK = "MAIN"
FORWARD_HOLD = "FWD"
AFT_HOLD = "AFT"
BULK_HOLD = "BULK"

COMPARTMENTS = (MAIN_DECK, FORWARD_HOLD, AFT_HOLD, BULK_HOLD)


@dataclass(frozen=True)
class Position:
    """One place on the aeroplane a load can go."""

    code: str
    compartment: str
    arm: Decimal
    max_weight: int
    length: Decimal
    width: Decimal
    max_running_load: int
    max_area_load: int
    accepts: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        code = self.code.strip().upper()
        if not code:
            raise DataError("a position needs a code")
        object.__setattr__(self, "code", code)
        compartment = self.compartment.strip().upper()
        if compartment not in COMPARTMENTS:
            raise DataError(f"position {code} is in no compartment this build knows: {compartment}")
        object.__setattr__(self, "compartment", compartment)
        object.__setattr__(self, "arm", to_metres(self.arm))
        object.__setattr__(self, "length", to_metres(self.length))
        object.__setattr__(self, "width", to_metres(self.width))
        object.__setattr__(self, "max_weight", to_kilos(self.max_weight, what="position weight"))
        if self.max_weight <= 0:
            raise DataError(f"position {code} has no weight limit")
        if self.length <= 0 or self.width <= 0:
            raise DataError(f"position {code} has no floor area")
        if self.max_running_load <= 0:
            raise DataError(f"position {code} has no running load limit")
        if self.max_area_load <= 0:
            raise DataError(f"position {code} has no area load limit")
        object.__setattr__(self, "accepts", tuple(sorted({base.upper() for base in self.accepts})))

    @property
    def bulk(self) -> bool:
        """A bulk position takes loose pieces and no ULD at all."""
        return not self.accepts

    @property
    def floor_area(self) -> Decimal:
        """Square metres of floor under the position."""
        return (self.length * self.width).quantize(Decimal("0.001"))

    def accepts_base(self, base: str) -> bool:
        """Whether a ULD of that base size can be put here."""
        return base.strip().upper() in self.accepts

    def running_load(self, weight: int) -> int:
        """Kilograms per metre of fuselage for a weight in this position."""
        return int((Decimal(weight) / self.length).to_integral_value(rounding="ROUND_CEILING"))

    def area_load(self, weight: int) -> int:
        """Kilograms per square metre of floor for a weight in this position."""
        return int((Decimal(weight) / self.floor_area).to_integral_value(rounding="ROUND_CEILING"))

    def over_weight_by(self, weight: int) -> int:
        """How far past the position limit a weight sits, zero when it fits."""
        return max(0, weight - self.max_weight)

    def describe(self) -> str:
        """One line for the loading instruction."""
        takes = "bulk" if self.bulk else "/".join(self.accepts)
        return f"{self.code} {self.compartment} arm {self.arm} max {self.max_weight} kg {takes}"
