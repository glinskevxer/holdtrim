"""What comes off when the aeroplane will not take it all.

Offloading is a commercial decision with an arithmetic constraint, and the two
get confused. The arithmetic says how many kilograms have to go. Which
kilograms is a matter of what was promised to whom, and that is what the
priority on each candidate carries: a courier shipment on a service level
agreement stays, a spot booking that turned up this morning goes.

Within a priority the heaviest goes first, because the point is to get inside
the limit in as few movements as possible. Every carton taken off a pallet is
a pallet that has to be broken down, restacked, reweighed and retagged, and
the ramp is not paid by the carton.
"""

from __future__ import annotations

from dataclasses import dataclass

from holdtrim.balance.limits import structural
from holdtrim.balance.loading import Balance
from holdtrim.errors import DataError
from holdtrim.units import to_kilos

STANDBY = 0
GENERAL = 1
CONTRACT = 2
PRIORITY = 3
LEVELS = (STANDBY, GENERAL, CONTRACT, PRIORITY)


@dataclass(frozen=True)
class Candidate:
    """Something that could come off, and how badly it wants to stay."""

    position: str
    weight: int
    uld: str = ""
    awb: str = ""
    priority: int = GENERAL

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", self.position.strip().upper())
        object.__setattr__(self, "weight", to_kilos(self.weight, what="candidate weight"))
        if self.weight <= 0:
            raise DataError(f"there is nothing in {self.position} to take off")
        if self.priority not in LEVELS:
            raise DataError(f"{self.priority} is not a priority this build knows")

    @property
    def label(self) -> str:
        """What to call it in the offload message."""
        return self.uld or self.awb or self.position

    def describe(self) -> str:
        """One line for the offload list."""
        return f"{self.label} from {self.position}, {self.weight} kg"


@dataclass(frozen=True)
class Offload:
    """What was chosen, and whether it was enough."""

    removed: tuple[Candidate, ...] = ()
    wanted: int = 0

    @property
    def weight(self) -> int:
        """How much this takes off."""
        return sum(candidate.weight for candidate in self.removed)

    @property
    def short_by(self) -> int:
        """How much more would still have to go."""
        return max(0, self.wanted - self.weight)

    @property
    def enough(self) -> bool:
        """Whether taking this off brings the flight inside its limits."""
        return self.short_by == 0

    @property
    def spare(self) -> int:
        """How much more came off than had to, which is nearly always some."""
        return max(0, self.weight - self.wanted)

    def describe(self) -> str:
        """One line for the handover."""
        if not self.removed:
            return "nothing to offload"
        return f"{len(self.removed)} item(s), {self.weight} kg, {self.spare} kg more than needed"


def excess(balance: Balance) -> int:
    """How much has to come off before the structural limits are met."""
    return max((finding.over_by for finding in structural(balance)), default=0)


def choose(candidates: tuple[Candidate, ...], wanted: int) -> Offload:
    """Pick what comes off, cheapest promise first and heaviest within that."""
    if wanted <= 0:
        return Offload(removed=(), wanted=0)
    ordered = sorted(candidates, key=lambda item: (item.priority, -item.weight, item.position))
    removed: list[Candidate] = []
    taken = 0
    for candidate in ordered:
        if taken >= wanted:
            break
        removed.append(candidate)
        taken += candidate.weight
    return Offload(removed=tuple(removed), wanted=wanted)


def for_balance(balance: Balance, candidates: tuple[Candidate, ...]) -> Offload:
    """What has to come off this flight, and what should be it."""
    return choose(candidates, excess(balance))
