"""The certified centre of gravity envelope, as a table of breakpoints.

The loading manual prints the envelope as a shape on graph paper. What it is
underneath is a forward index limit and an aft index limit at each of a handful
of weights, with straight lines between them. Reading a limit at a weight in
between means interpolating along those lines, which is what the graph paper
was doing by eye.

There is one envelope per weight the aeroplane is checked at: zero fuel,
takeoff and landing. They are different shapes and a load can sit inside one
and outside another.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.errors import DataError, RuleError
from holdtrim.units import to_index, to_kilos

ZERO_FUEL = "zero fuel"
TAKEOFF = "takeoff"
LANDING = "landing"


@dataclass(frozen=True)
class EnvelopePoint:
    """The forward and aft index limits at one weight."""

    weight: int
    forward_index: Decimal
    aft_index: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "weight", to_kilos(self.weight, what="envelope weight"))
        object.__setattr__(self, "forward_index", to_index(self.forward_index))
        object.__setattr__(self, "aft_index", to_index(self.aft_index))
        if self.forward_index >= self.aft_index:
            raise DataError(
                f"at {self.weight} kg the forward limit {self.forward_index} is not "
                f"forward of the aft limit {self.aft_index}"
            )

    @property
    def width(self) -> Decimal:
        """How many index units wide the envelope is at this weight."""
        return to_index(self.aft_index - self.forward_index)


@dataclass(frozen=True)
class Envelope:
    """One certified envelope, read at any weight it covers."""

    name: str
    points: tuple[EnvelopePoint, ...]

    def __post_init__(self) -> None:
        name = self.name.strip().lower()
        if not name:
            raise DataError("an envelope needs a name")
        object.__setattr__(self, "name", name)
        if len(self.points) < 2:
            raise DataError(f"the {name} envelope needs at least two breakpoints")
        weights = [point.weight for point in self.points]
        if weights != sorted(weights) or len(set(weights)) != len(weights):
            raise DataError(f"the {name} envelope breakpoints are not in weight order")

    @property
    def lightest(self) -> int:
        """The lightest weight the envelope is drawn for."""
        return self.points[0].weight

    @property
    def heaviest(self) -> int:
        """The heaviest weight the envelope is drawn for."""
        return self.points[-1].weight

    def covers(self, weight: int) -> bool:
        """Whether the envelope says anything at all at that weight."""
        return self.lightest <= weight <= self.heaviest

    def limits_at(self, weight: int) -> tuple[Decimal, Decimal]:
        """The forward and aft index limits at a weight, interpolated."""
        if not self.covers(weight):
            raise RuleError(
                f"{weight} kg is outside the {self.name} envelope, which runs "
                f"{self.lightest} to {self.heaviest} kg"
            )
        below = self.points[0]
        for point in self.points:
            if point.weight == weight:
                return point.forward_index, point.aft_index
            if point.weight < weight:
                below = point
            else:
                span = Decimal(point.weight - below.weight)
                along = Decimal(weight - below.weight) / span
                forward = below.forward_index + (point.forward_index - below.forward_index) * along
                aft = below.aft_index + (point.aft_index - below.aft_index) * along
                return to_index(forward), to_index(aft)
        raise RuleError(f"{weight} kg fell off the {self.name} envelope")  # pragma: no cover

    def contains(self, weight: int, index: Decimal) -> bool:
        """Whether a weight and index pair sits inside the shape."""
        forward, aft = self.limits_at(weight)
        return forward <= to_index(index) <= aft

    def margin(self, weight: int, index: Decimal) -> Decimal:
        """Index units to the nearer edge, negative when it is outside."""
        forward, aft = self.limits_at(weight)
        here = to_index(index)
        if here < forward:
            return to_index(here - forward)
        if here > aft:
            return to_index(aft - here)
        return to_index(min(here - forward, aft - here))

    def widest(self) -> EnvelopePoint:
        """The breakpoint with the most room in it."""
        return max(self.points, key=lambda point: point.width)
