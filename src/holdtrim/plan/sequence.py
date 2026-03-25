"""The order things are loaded in, which is not the order they appear on the plan.

A plan that is inside the envelope when it is finished can be outside it half
way through, and half way through is a real aeroplane standing on a real ramp.
Load three pallets into the aft positions first and the centre of gravity walks
straight out of the back of the envelope while the front of the aeroplane is
still empty.

So the sequence is checked step by step, and the suggested order alternates:
the most forward load, then the most aft, then the next most forward, working
inwards. That keeps the running centre of gravity near the middle instead of
letting it drift to one end and come back.

Unloading is the same problem in reverse and gets the reverse order, for the
same reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.balance.index import index_of
from holdtrim.errors import DataError
from holdtrim.model.aircraft import AircraftType
from holdtrim.model.envelope import ZERO_FUEL
from holdtrim.model.tail import Tail
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.units import to_index


@dataclass(frozen=True)
class Step:
    """One position loaded, and where that leaves the aeroplane."""

    order: int
    position: str
    weight: int
    running_weight: int
    running_index: Decimal
    inside: bool

    def describe(self) -> str:
        """One line for the loading instruction."""
        state = "inside" if self.inside else "OUTSIDE"
        return (
            f"{self.order}. {self.position} {self.weight} kg, "
            f"then {self.running_weight} kg at index {self.running_index} ({state})"
        )


def walk(kind: AircraftType, tail: Tail, order: tuple[Assignment, ...]) -> tuple[Step, ...]:
    """Work an order of loading step by step, reading the envelope at each one."""
    shape = kind.envelope(ZERO_FUEL)
    weight = tail.dry_operating_weight
    index = tail.dry_operating_index
    steps = []
    for number, assignment in enumerate(order, start=1):
        arm = kind.layout.position(assignment.position).arm
        weight += assignment.weight
        index = to_index(index + index_of(assignment.weight, arm, kind.geometry))
        inside = shape.covers(weight) and shape.contains(weight, index)
        steps.append(
            Step(
                order=number,
                position=assignment.position,
                weight=assignment.weight,
                running_weight=weight,
                running_index=index,
                inside=inside,
            )
        )
    return tuple(steps)


def outside(steps: tuple[Step, ...]) -> tuple[Step, ...]:
    """The steps where the aeroplane is not inside its envelope."""
    return tuple(step for step in steps if not step.inside)


def suggested(kind: AircraftType, plan: LoadPlan) -> tuple[Assignment, ...]:
    """An order that works from both ends inwards."""
    if plan.empty:
        return ()
    by_arm = sorted(plan.assignments, key=lambda entry: kind.layout.position(entry.position).arm)
    order = []
    while by_arm:
        order.append(by_arm.pop(0))
        if by_arm:
            order.append(by_arm.pop())
    return tuple(order)


def as_planned(plan: LoadPlan) -> tuple[Assignment, ...]:
    """The order the plan happens to be written in, which nobody chose."""
    return plan.assignments


def unloading(order: tuple[Assignment, ...]) -> tuple[Assignment, ...]:
    """The reverse, which is the order things come off."""
    return tuple(reversed(order))


def instruction(steps: tuple[Step, ...]) -> tuple[str, ...]:
    """The loading instruction, one line a step."""
    if not steps:
        raise DataError("there is nothing to load")
    return tuple(step.describe() for step in steps)
