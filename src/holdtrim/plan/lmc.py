"""Last minute changes, and the point at which they stop being last minute.

Once a loadsheet is issued the figures on it are what the crew have. A small
change after that can be written in the last minute change box and initialled,
because the arithmetic is easy enough to do on the aircraft and the error it
introduces is small. A large change cannot, because past a certain size nobody
can be sure the aeroplane is still inside its envelope without doing the whole
calculation again.

The line between the two is a weight the operator sets, and it applies to the
total of the changes rather than to each one. Three changes of two hundred
kilograms are not three small changes, they are one six hundred kilogram change
written down in three places.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.balance.index import index_of
from holdtrim.errors import DataError, RuleError
from holdtrim.model.aircraft import AircraftType
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.units import to_index

TOLERANCE = 500
ADDED = "added"
OFFLOADED = "offloaded"


@dataclass(frozen=True)
class Change:
    """One thing put on or taken off after the sheet was issued."""

    position: str
    weight: int
    what: str = ""

    def __post_init__(self) -> None:
        position = self.position.strip().upper()
        if not position:
            raise DataError("a last minute change needs a position")
        object.__setattr__(self, "position", position)
        if self.weight == 0:
            raise DataError(f"a change of nothing at {position} is not a change")
        object.__setattr__(self, "what", self.what.strip())

    @property
    def direction(self) -> str:
        """Whether this put weight on or took it off."""
        return ADDED if self.weight > 0 else OFFLOADED

    @property
    def size(self) -> int:
        """How big the change is, whichever way it went."""
        return abs(self.weight)

    def describe(self) -> str:
        """One line for the last minute change box."""
        what = f" {self.what}" if self.what else ""
        return f"{self.direction} {self.size} kg at {self.position}{what}"


@dataclass(frozen=True)
class Changes:
    """Every change made after issue, and the limit they are read against."""

    changes: tuple[Change, ...] = ()
    tolerance: int = TOLERANCE

    def __post_init__(self) -> None:
        if self.tolerance <= 0:
            raise DataError("a last minute change tolerance has to be a weight")

    @property
    def net(self) -> int:
        """What the changes do to the payload, taking direction into account."""
        return sum(change.weight for change in self.changes)

    @property
    def total(self) -> int:
        """How much weight was handled, ignoring direction."""
        return sum(change.size for change in self.changes)

    @property
    def within_tolerance(self) -> bool:
        """Whether these may go in the box rather than on a new sheet."""
        return self.total <= self.tolerance

    @property
    def over_by(self) -> int:
        """How far past the tolerance the changes are."""
        return max(0, self.total - self.tolerance)

    @property
    def empty(self) -> bool:
        """Whether anything changed at all."""
        return not self.changes

    def index_change(self, kind: AircraftType) -> Decimal:
        """What the changes do to the index."""
        moved = Decimal("0.0")
        for change in self.changes:
            arm = kind.layout.position(change.position).arm
            moved += index_of(abs(change.weight), arm, kind.geometry) * (
                1 if change.weight > 0 else -1
            )
        return to_index(moved)

    def add(self, change: Change) -> Changes:
        """Record another change."""
        return Changes(changes=(*self.changes, change), tolerance=self.tolerance)

    def lines(self) -> tuple[str, ...]:
        """The box as it is written on the sheet."""
        if self.empty:
            return ("none",)
        return tuple(change.describe() for change in self.changes)


def applied(plan: LoadPlan, changes: Changes) -> LoadPlan:
    """The plan with the changes worked into it, refusing anything impossible."""
    weights = dict(plan.weights)
    for change in changes.changes:
        standing = weights.get(change.position, 0)
        wanted = standing + change.weight
        if wanted < 0:
            raise RuleError(
                f"{change.size} kg cannot come off {change.position}, "
                f"which is only carrying {standing} kg"
            )
        weights[change.position] = wanted
    kept = []
    for assignment in plan.assignments:
        weight = weights.pop(assignment.position, 0)
        if weight <= 0:
            continue
        kept.append(
            Assignment(
                position=assignment.position,
                weight=weight,
                uld=assignment.uld,
                destination=assignment.destination,
            )
        )
    for position, weight in sorted(weights.items()):
        if weight > 0:
            kept.append(Assignment(position=position, weight=weight))
    return LoadPlan(flight_key=plan.flight_key, assignments=tuple(kept), edition=plan.edition)


def check_tolerance(changes: Changes) -> None:
    """Refuse changes that need the whole sheet doing again."""
    if not changes.within_tolerance:
        raise RuleError(
            f"{changes.total} kg of last minute changes is {changes.over_by} kg past "
            f"the {changes.tolerance} kg tolerance, issue a new loadsheet"
        )
