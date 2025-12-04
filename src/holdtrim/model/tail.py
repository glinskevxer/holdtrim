"""One aeroplane, as opposed to one type of aeroplane.

What belongs to the tail and not to the type is what it weighs. Dry operating
weight is the aeroplane ready to work with no payload and no usable fuel:
airframe, crew, their bags, the loading equipment that lives on board and the
fluids that are not burned. Its index is the matching figure on the schedule's
index scale.

Both come off a weighing, and a weighing goes out of date. An operator on the
fleet method reweighs on a cycle, and flying on an expired one is a finding,
so the expiry is on the record rather than in somebody's diary.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from holdtrim.errors import DataError
from holdtrim.ids import parse_registration
from holdtrim.units import to_index, to_kilos

IN_SERVICE = "in service"
MAINTENANCE = "maintenance"
STORED = "stored"
STATUSES = (IN_SERVICE, MAINTENANCE, STORED)

WEIGHING_VALID_MONTHS = 60


def add_months(when: date, months: int) -> date:
    """The same day of the month that many months on, clipped to month end."""
    total = when.month - 1 + months
    year = when.year + total // 12
    month = total % 12 + 1
    day = when.day
    while day > 28:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1
    return date(year, month, day)


@dataclass(frozen=True)
class Tail:
    """A registered aeroplane and the weights the office loads it on."""

    registration: str
    type_code: str
    dry_operating_weight: int
    dry_operating_index: Decimal
    weighed_on: date
    serial_number: str = ""
    status: str = IN_SERVICE
    weighing_valid_months: int = WEIGHING_VALID_MONTHS

    def __post_init__(self) -> None:
        object.__setattr__(self, "registration", parse_registration(self.registration))
        type_code = self.type_code.strip().upper()
        if not type_code:
            raise DataError(f"{self.registration} is not tied to a type")
        object.__setattr__(self, "type_code", type_code)
        object.__setattr__(
            self,
            "dry_operating_weight",
            to_kilos(self.dry_operating_weight, what="dry operating weight"),
        )
        if self.dry_operating_weight <= 0:
            raise DataError(f"{self.registration} has no dry operating weight")
        object.__setattr__(self, "dry_operating_index", to_index(self.dry_operating_index))
        object.__setattr__(self, "serial_number", self.serial_number.strip())
        status = self.status.strip().lower()
        if status not in STATUSES:
            raise DataError(f"{self.registration} is in no status this build knows: {status}")
        object.__setattr__(self, "status", status)
        if self.weighing_valid_months <= 0:
            raise DataError(f"{self.registration} has a weighing that is valid for no time at all")

    @property
    def weighing_expires(self) -> date:
        """The day after which the weighing no longer counts."""
        return add_months(self.weighed_on, self.weighing_valid_months)

    def weighing_current(self, on: date) -> bool:
        """Whether the weighing still stands on a given day."""
        return on <= self.weighing_expires

    def days_of_weighing_left(self, on: date) -> int:
        """Days until the weighing expires, negative once it has."""
        return (self.weighing_expires - on).days

    @property
    def loadable(self) -> bool:
        """Only an in service aeroplane gets a load plan."""
        return self.status == IN_SERVICE

    def with_variation(self, weight: int, index: Decimal) -> Tail:
        """The same tail with a variation applied to its dry operating figures.

        A pantry taken out or a spare wheel put on board changes both numbers
        together, and the pair only means anything applied together.
        """
        return replace(
            self,
            dry_operating_weight=self.dry_operating_weight + weight,
            dry_operating_index=to_index(self.dry_operating_index + index),
        )

    def describe(self) -> str:
        """One line for a fleet listing."""
        return (
            f"{self.registration} {self.type_code} DOW {self.dry_operating_weight} kg "
            f"DOI {self.dry_operating_index} ({self.status})"
        )
