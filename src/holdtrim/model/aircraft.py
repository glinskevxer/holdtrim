"""What the weight schedule says about a type of aeroplane.

Two things live here and they are easy to confuse.

The structural limits are certificate numbers. They belong to the type and no
loading decision can move them.

The geometry is how this type's weight schedule turns a weight at an arm into
an index, and an index back into a percentage of mean aerodynamic chord. Index
is an arbitrary scale chosen by whoever wrote the schedule: a constant divisor
so the numbers stay small, and a constant added so they stay positive. The two
constants are meaningless on their own and mean everything together.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.errors import DataError
from holdtrim.units import to_index, to_kilos, to_metres

TYPE_CODE_LENGTH = (3, 5)


@dataclass(frozen=True)
class StructuralLimits:
    """The four weights on the certificate, in kilograms."""

    max_ramp: int
    max_takeoff: int
    max_landing: int
    max_zero_fuel: int

    def __post_init__(self) -> None:
        for field, value in self.as_dict().items():
            if value <= 0:
                raise DataError(f"{field.replace('_', ' ')} must be a positive weight")
        if self.max_ramp < self.max_takeoff:
            raise DataError("max ramp weight cannot be below max takeoff weight")
        if self.max_takeoff < self.max_landing:
            raise DataError("max takeoff weight cannot be below max landing weight")
        if self.max_landing < self.max_zero_fuel:
            raise DataError("max landing weight cannot be below max zero fuel weight")

    def as_dict(self) -> dict[str, int]:
        """The four figures keyed by name, for reports and for checking."""
        return {
            "max_ramp": self.max_ramp,
            "max_takeoff": self.max_takeoff,
            "max_landing": self.max_landing,
            "max_zero_fuel": self.max_zero_fuel,
        }

    @property
    def taxi_allowance(self) -> int:
        """How much fuel may be burned between the stand and the runway."""
        return self.max_ramp - self.max_takeoff


@dataclass(frozen=True)
class MacGeometry:
    """The constants that turn weight and arm into index and percent MAC."""

    reference_arm: Decimal
    lemac: Decimal
    mac_length: Decimal
    index_constant: Decimal
    index_reference: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_arm", to_metres(self.reference_arm))
        object.__setattr__(self, "lemac", to_metres(self.lemac))
        object.__setattr__(self, "mac_length", to_metres(self.mac_length))
        object.__setattr__(self, "index_constant", to_metres(self.index_constant))
        object.__setattr__(self, "index_reference", to_index(self.index_reference))
        if self.mac_length <= 0:
            raise DataError("the mean aerodynamic chord must have a length")
        if self.index_constant <= 0:
            raise DataError("the index constant must be positive")

    @property
    def trailing_edge(self) -> Decimal:
        """The arm at the trailing edge of the chord."""
        return to_metres(self.lemac + self.mac_length)

    def percent_of_mac(self, arm: Decimal) -> Decimal:
        """Where an arm sits along the chord, as a percentage."""
        return ((arm - self.lemac) / self.mac_length * 100).quantize(
            Decimal("0.1"), rounding="ROUND_HALF_UP"
        )

    def arm_at_percent(self, percent: Decimal) -> Decimal:
        """The arm a percentage of chord corresponds to."""
        return to_metres(self.lemac + self.mac_length * percent / 100)


@dataclass(frozen=True)
class AircraftType:
    """A type of aeroplane and the schedule its loads are worked out on."""

    code: str
    name: str
    limits: StructuralLimits
    geometry: MacGeometry
    empty_weight: int = 0

    def __post_init__(self) -> None:
        code = self.code.strip().upper()
        low, high = TYPE_CODE_LENGTH
        if not low <= len(code) <= high or not code.isalnum():
            raise DataError(f"type code {self.code!r} is not three to five letters or digits")
        object.__setattr__(self, "code", code)
        name = self.name.strip()
        if not name:
            raise DataError(f"type {code} has no name")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "empty_weight", to_kilos(self.empty_weight, what="empty weight"))
        if self.empty_weight and self.empty_weight >= self.limits.max_zero_fuel:
            raise DataError(f"type {code} weighs more empty than its max zero fuel weight")

    @property
    def structural_payload(self) -> int:
        """The most payload the certificate allows, before any fuel."""
        return self.limits.max_zero_fuel - self.empty_weight

    def describe(self) -> str:
        """One line for a fleet listing."""
        return f"{self.code} {self.name} MZFW {self.limits.max_zero_fuel} kg"
