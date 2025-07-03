"""Putting the load somewhere, and saying plainly what would not fit.

The rule of thumb a load controller works to is heavy loads near the centre of
gravity and light loads at the ends, because that keeps the trim in the middle
of the envelope where a late change does not push it out. This does the same
thing arithmetically: it places the heaviest item first, and for each item it
picks the position that leaves the index closest to the middle of the zero fuel
envelope.

It is a suggestion, not a decision. Anything it could not place comes back with
the reason, and the plan it produces still goes through the same limit checks a
hand built plan does. A planner that quietly dropped what would not fit would
be worse than no planner at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.balance.index import index_of
from holdtrim.errors import DataError
from holdtrim.model.aircraft import AircraftType
from holdtrim.model.envelope import ZERO_FUEL
from holdtrim.model.position import Position
from holdtrim.model.tail import Tail
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.units import to_index, to_kilos

NO_POSITION_TAKES_IT = "no free position takes that base size"
EVERY_POSITION_TOO_SMALL = "every free position that takes it is too small"
COMBINED_LIMIT = "it would break a combined limit wherever it went"


@dataclass(frozen=True)
class Item:
    """One thing waiting to be given a position."""

    label: str
    weight: int
    base: str = ""
    destination: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "label", self.label.strip().upper())
        object.__setattr__(self, "base", self.base.strip().upper())
        object.__setattr__(self, "weight", to_kilos(self.weight, what="item weight"))
        if self.weight <= 0:
            raise DataError(f"{self.label or 'a loose load'} weighs nothing")

    @property
    def loose(self) -> bool:
        """An item with no base size is loose cargo for a bulk position."""
        return self.base == ""


@dataclass(frozen=True)
class Allocation:
    """What was planned, and what was left on the ground."""

    plan: LoadPlan
    unplaced: tuple[tuple[Item, str], ...] = ()

    @property
    def complete(self) -> bool:
        """Whether everything offered found a position."""
        return not self.unplaced

    def reason_for(self, label: str) -> str:
        """Why one item was not placed."""
        wanted = label.strip().upper()
        for item, reason in self.unplaced:
            if item.label == wanted:
                return reason
        raise DataError(f"{wanted} was placed, or was never offered")


def target_index(kind: AircraftType, weight: int) -> Decimal:
    """The middle of the zero fuel envelope at a weight, which is where to aim."""
    shape = kind.envelope(ZERO_FUEL)
    held = min(max(weight, shape.lightest), shape.heaviest)
    forward, aft = shape.limits_at(held)
    return to_index((forward + aft) / 2)


def _candidates(kind: AircraftType, item: Item, taken: set[str]) -> tuple[Position, ...]:
    free = tuple(p for p in kind.layout.by_arm() if p.code not in taken)
    if item.loose:
        return tuple(p for p in free if p.bulk)
    return tuple(p for p in free if p.accepts_base(item.base))


def _breaks_combined(kind: AircraftType, weights: dict[str, int]) -> bool:
    return any(limit.over_by(weights) for limit in kind.layout.cumulative)


def allocate(kind: AircraftType, tail: Tail, items: tuple[Item, ...]) -> Allocation:
    """Place items into positions, heaviest first, aiming at the middle."""
    ordered = sorted(items, key=lambda item: (-item.weight, item.label))
    total = tail.dry_operating_weight + sum(item.weight for item in ordered)
    aim = target_index(kind, total)
    assignments: list[Assignment] = []
    weights: dict[str, int] = {}
    running = tail.dry_operating_index
    unplaced: list[tuple[Item, str]] = []
    for item in ordered:
        taken = set(weights)
        candidates = _candidates(kind, item, taken)
        if not candidates:
            unplaced.append((item, NO_POSITION_TAKES_IT))
            continue
        fitting = [p for p in candidates if p.over_weight_by(item.weight) == 0]
        if not fitting:
            unplaced.append((item, EVERY_POSITION_TOO_SMALL))
            continue
        legal = [p for p in fitting if not _breaks_combined(kind, {**weights, p.code: item.weight})]
        if not legal:
            unplaced.append((item, COMBINED_LIMIT))
            continue
        chosen = min(
            legal,
            key=lambda p: (
                abs(running + index_of(item.weight, p.arm, kind.geometry) - aim),
                p.code,
            ),
        )
        running = to_index(running + index_of(item.weight, chosen.arm, kind.geometry))
        weights[chosen.code] = item.weight
        assignments.append(
            Assignment(
                position=chosen.code,
                weight=item.weight,
                uld=item.label if not item.loose else "",
                destination=item.destination,
            )
        )
    plan = LoadPlan(flight_key=_key_placeholder(), assignments=tuple(assignments))
    return Allocation(plan=plan, unplaced=tuple(unplaced))


def _key_placeholder() -> str:
    """A plan has to belong to a flight, and the caller attaches it to one."""
    return "unassigned"


def for_flight(
    flight_key: str, kind: AircraftType, tail: Tail, items: tuple[Item, ...]
) -> Allocation:
    """Allocate and label the plan with the flight it is for."""
    made = allocate(kind, tail, items)
    plan = LoadPlan(flight_key=flight_key, assignments=made.plan.assignments)
    return Allocation(plan=plan, unplaced=made.unplaced)
