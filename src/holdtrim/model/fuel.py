"""What the fuel does to the index.

This is part of the weight schedule rather than part of the calculation, which
is why it sits with the model and not with the arithmetic that uses it. It was
in the balance package to begin with and that made the type depend on the
calculation, which is backwards: the schedule is the thing that is published
and the arithmetic is the thing that reads it.

Fuel is not a load at a fixed arm. The tanks are in the wing and they fill and
empty in a sequence, so the centre of gravity of the fuel moves as the quantity
changes, and it does not move in a straight line. The schedule handles this by
printing a table: at this many kilograms of fuel, apply this index correction.

So the fuel index is read off a curve rather than worked out from an arm, and
reading it between two printed rows means interpolating. That is the one place
in the whole calculation where the arithmetic is an approximation, and it is
the schedule's approximation rather than ours.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.errors import DataError, RuleError
from holdtrim.units import to_index, to_kilos


@dataclass(frozen=True)
class FuelPoint:
    """One printed row of the fuel index table."""

    weight: int
    index: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "weight", to_kilos(self.weight, what="fuel weight"))
        object.__setattr__(self, "index", to_index(self.index))


@dataclass(frozen=True)
class FuelTable:
    """The whole table, read at any quantity between its ends."""

    points: tuple[FuelPoint, ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise DataError("a fuel index table needs at least two rows")
        weights = [point.weight for point in self.points]
        if weights != sorted(weights) or len(set(weights)) != len(weights):
            raise DataError("the fuel index table rows are not in weight order")
        if weights[0] != 0:
            raise DataError("the fuel index table has to start at zero fuel")

    @property
    def capacity(self) -> int:
        """The most fuel the table is printed for."""
        return self.points[-1].weight

    def covers(self, weight: int) -> bool:
        """Whether the table says anything at that quantity."""
        return 0 <= weight <= self.capacity

    def index_at(self, weight: int) -> Decimal:
        """The index correction for a quantity of fuel."""
        if not self.covers(weight):
            raise RuleError(
                f"{weight} kg of fuel is off the table, which runs 0 to {self.capacity} kg"
            )
        below = self.points[0]
        for point in self.points:
            if point.weight == weight:
                return point.index
            if point.weight < weight:
                below = point
            else:
                span = Decimal(point.weight - below.weight)
                along = Decimal(weight - below.weight) / span
                return to_index(below.index + (point.index - below.index) * along)
        raise RuleError(f"{weight} kg of fuel fell off the table")  # pragma: no cover

    def burn_between(self, start: int, finish: int) -> Decimal:
        """What burning from one quantity to another does to the index."""
        return to_index(self.index_at(finish) - self.index_at(start))

    def rows(self) -> tuple[tuple[int, Decimal], ...]:
        """The table as it is printed, for a report."""
        return tuple((point.weight, point.index) for point in self.points)
