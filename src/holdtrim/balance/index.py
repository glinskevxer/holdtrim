"""Index arithmetic.

The index of a load is

    K + sum over every item of  weight * (arm - reference arm) / C

where K is the schedule's index reference and C its index constant. Both come
off the weight schedule and neither means anything on its own.

Two things follow that are worth saying out loud, because both have bitten
somebody. An item sitting exactly at the reference arm contributes nothing at
all, whatever it weighs. And an index cannot be turned back into a centre of
gravity without knowing the weight it belongs to, which is why every function
here that reads a position takes the weight as well.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from holdtrim.errors import DataError
from holdtrim.model.aircraft import MacGeometry
from holdtrim.units import to_index, to_metres


@dataclass(frozen=True)
class Contribution:
    """One weight at one arm, and what it does to the index."""

    label: str
    weight: int
    arm: Decimal

    def influence(self, geometry: MacGeometry) -> Decimal:
        """The index units this item adds, positive aft of the reference."""
        return index_of(self.weight, self.arm, geometry)


def index_of(weight: int, arm: Decimal, geometry: MacGeometry) -> Decimal:
    """What a weight at an arm does to the index, before rounding to the sheet."""
    moment = Decimal(weight) * (to_metres(arm) - geometry.reference_arm)
    return to_index(moment / geometry.index_constant)


def total_index(
    contributions: Iterable[Contribution], geometry: MacGeometry, *, base: Decimal
) -> Decimal:
    """A starting index plus everything loaded on top of it."""
    running = to_index(base)
    for contribution in contributions:
        running += contribution.influence(geometry)
    return to_index(running)


def arm_of_index(weight: int, index: Decimal, geometry: MacGeometry) -> Decimal:
    """Where the centre of gravity sits for an index at a weight."""
    if weight <= 0:
        raise DataError("an index cannot be read as an arm at zero weight")
    offset = (
        (to_index(index) - geometry.index_reference) * geometry.index_constant / Decimal(weight)
    )
    return to_metres(geometry.reference_arm + offset)


def percent_mac(weight: int, index: Decimal, geometry: MacGeometry) -> Decimal:
    """The centre of gravity as a percentage of chord, which is what is signed for."""
    return geometry.percent_of_mac(arm_of_index(weight, index, geometry))


def index_at_percent(weight: int, percent: Decimal, geometry: MacGeometry) -> Decimal:
    """The index a weight would have to carry to sit at that percentage."""
    if weight <= 0:
        raise DataError("a percentage of chord means nothing at zero weight")
    arm = geometry.arm_at_percent(percent)
    return to_index(
        geometry.index_reference
        + Decimal(weight) * (arm - geometry.reference_arm) / geometry.index_constant
    )


def shift(weight: int, from_arm: Decimal, to_arm: Decimal, geometry: MacGeometry) -> Decimal:
    """What moving a load from one position to another does to the index."""
    return to_index(index_of(weight, to_arm, geometry) - index_of(weight, from_arm, geometry))
