"""How much more will go in each position.

The question a load controller is asked twenty times a night is not whether the
plan is legal, it is whether one more pallet will go, and where. That is not
the position limit: a position with 800 kg of room by its own placard can be
full because of a combined limit, because the zero fuel weight is nearly there,
or because another kilogram aft takes the centre of gravity out of the
envelope.

So the answer is worked out by asking the real checks. The weight is found by
halving the range rather than by adding a kilogram at a time, because the
checks are not cheap and the answer is monotonic: if a weight passes, every
smaller weight passes too.
"""

from __future__ import annotations

from dataclasses import dataclass

from holdtrim.balance.limits import check
from holdtrim.balance.loading import Balance, load_positions
from holdtrim.model.aircraft import AircraftType
from holdtrim.model.tail import Tail
from holdtrim.plan.loadplan import LoadPlan


@dataclass(frozen=True)
class Room:
    """How much more one position will take."""

    position: str
    holding: int
    spare: int

    @property
    def full(self) -> bool:
        """Whether nothing more will go in it."""
        return self.spare == 0

    def describe(self) -> str:
        """One line for the room report."""
        return f"{self.position} holding {self.holding} kg, {self.spare} kg more will go"


def _passes(
    kind: AircraftType, tail: Tail, weights: dict[str, int], fuel: tuple[int, int, int]
) -> bool:
    taxi, trip, takeoff = fuel
    balance = Balance(
        kind=kind,
        tail=tail,
        loads=load_positions(kind, weights),
        taxi_fuel=taxi,
        trip_fuel=trip,
        takeoff_fuel=takeoff,
    )
    return not check(balance)


def spare_in(
    kind: AircraftType,
    tail: Tail,
    plan: LoadPlan,
    position: str,
    *,
    fuel: tuple[int, int, int],
) -> int:
    """The most that could be added to one position with everything still legal."""
    code = kind.layout.position(position).code
    weights = dict(plan.weights)
    holding = weights.get(code, 0)
    if not _passes(kind, tail, weights, fuel):
        return 0
    low = 0
    high = kind.layout.position(code).max_weight - holding
    while low < high:
        middle = (low + high + 1) // 2
        weights[code] = holding + middle
        if _passes(kind, tail, weights, fuel):
            low = middle
        else:
            high = middle - 1
    return low


def everywhere(
    kind: AircraftType, tail: Tail, plan: LoadPlan, *, fuel: tuple[int, int, int]
) -> tuple[Room, ...]:
    """How much more each position will take, most room first."""
    found = []
    for position in kind.layout.by_arm():
        found.append(
            Room(
                position=position.code,
                holding=plan.weights.get(position.code, 0),
                spare=spare_in(kind, tail, plan, position.code, fuel=fuel),
            )
        )
    return tuple(sorted(found, key=lambda entry: (-entry.spare, entry.position)))


def best(report: tuple[Room, ...]) -> str:
    """The position with the most room, empty where there is none anywhere."""
    if not report or report[0].spare == 0:
        return ""
    return report[0].position
