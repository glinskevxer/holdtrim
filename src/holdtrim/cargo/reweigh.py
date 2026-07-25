"""Correcting a weight that was wrong, and noticing when it was very wrong.

Weights get corrected all the time. A shipper declares what they think the
shipment weighs, the shed puts it on the scales, and the two differ. That is
ordinary and it is why the scales are there.

What is not ordinary is a correction of a third. That is usually a units
mistake, a decimal point, or a shipment that is not the shipment on the
paperwork, and all three are worth stopping for. So a correction is applied
either way and reported when it is large, because refusing it would only mean
somebody deleting the row and typing it again.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.errors import DataError
from holdtrim.findings import STOP, WATCH, Finding
from holdtrim.units import to_kilos

REWEIGH = "reweigh"
LARGE_CHANGE = Decimal("0.25")


@dataclass(frozen=True)
class Correction:
    """One weight before and after."""

    what: str
    was: int
    now: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "was", to_kilos(self.was, what="weight before"))
        object.__setattr__(self, "now", to_kilos(self.now, what="weight after"))
        if self.was <= 0:
            raise DataError(f"{self.what} had no weight to correct")
        if self.now <= 0:
            raise DataError(f"{self.what} cannot be corrected to nothing")

    @property
    def difference(self) -> int:
        """How much it moved, signed."""
        return self.now - self.was

    @property
    def share(self) -> Decimal:
        """How much it moved as a share of what it was."""
        return (Decimal(abs(self.difference)) / Decimal(self.was)).quantize(Decimal("0.001"))

    @property
    def large(self) -> bool:
        """Whether the correction is big enough to be worth stopping for."""
        return self.share >= LARGE_CHANGE

    @property
    def heavier(self) -> bool:
        """Whether the thing turned out to weigh more."""
        return self.difference > 0

    def describe(self) -> str:
        """One line for the correction log."""
        way = "heavier" if self.heavier else "lighter"
        return f"{self.what} {self.was} kg became {self.now} kg, {abs(self.difference)} kg {way}"


def check(correction: Correction) -> tuple[Finding, ...]:
    """Whether a correction is worth somebody looking at."""
    if not correction.large:
        return ()
    percent = correction.share * 100
    return (
        Finding(
            check=REWEIGH,
            where=correction.what,
            detail=(
                f"moved by {percent.quantize(Decimal('0.1'))} percent, check the units "
                "and the paperwork"
            ),
            over_by=abs(correction.difference),
            severity=STOP if correction.share >= 1 else WATCH,
        ),
    )
