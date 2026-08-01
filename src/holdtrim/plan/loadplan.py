"""What goes in which position, before anything is checked against a limit.

The plan is a list of assignments and nothing else. It does not know the
aeroplane's limits, it does not know the envelope, and it deliberately does not
refuse a plan that is too heavy. Working out whether a plan is legal is a
separate job with its own module, because a load controller builds an illegal
plan on the way to a legal one all the time and a structure that refuses to
hold one is a structure that gets worked around.

What the plan does enforce is that it makes sense as a plan: one thing per
position, nothing weighing nothing, and no device loaded twice.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from holdtrim.errors import DataError, NotFoundError, RuleError
from holdtrim.ids import parse_station, parse_uld
from holdtrim.units import to_kilos

BULK = "bulk"


@dataclass(frozen=True)
class Assignment:
    """One position and what has been put in it."""

    position: str
    weight: int
    uld: str = ""
    destination: str = ""

    def __post_init__(self) -> None:
        position = self.position.strip().upper()
        if not position:
            raise DataError("an assignment needs a position")
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "weight", to_kilos(self.weight, what="assigned weight"))
        if self.weight <= 0:
            raise DataError(f"position {position} has been given nothing to hold")
        if self.uld:
            object.__setattr__(self, "uld", parse_uld(self.uld).formatted())
        if self.destination:
            object.__setattr__(self, "destination", parse_station(self.destination))

    @property
    def loose(self) -> bool:
        """A position with no device in it is loose cargo."""
        return self.uld == ""

    def describe(self) -> str:
        """One line for the loading instruction."""
        what = self.uld if self.uld else BULK
        where = f" for {self.destination}" if self.destination else ""
        return f"{self.position} {what} {self.weight} kg{where}"


@dataclass(frozen=True)
class LoadPlan:
    """Everything assigned to a flight, at one edition of the plan."""

    flight_key: str
    assignments: tuple[Assignment, ...] = ()
    edition: int = 1

    def __post_init__(self) -> None:
        if not self.flight_key.strip():
            raise DataError("a load plan has to belong to a flight")
        positions = [assignment.position for assignment in self.assignments]
        if len(set(positions)) != len(positions):
            raise DataError("a position has been assigned twice in one plan")
        devices = [a.uld for a in self.assignments if a.uld]
        if len(set(devices)) != len(devices):
            raise DataError("a device has been assigned to two positions")
        if self.edition < 1:
            raise DataError("a plan starts at edition one")

    @property
    def payload(self) -> int:
        """Everything on board, in kilograms."""
        return sum(assignment.weight for assignment in self.assignments)

    @property
    def weights(self) -> dict[str, int]:
        """Position code against weight, which is what the checks want."""
        return {a.position: a.weight for a in self.assignments}

    @property
    def devices(self) -> tuple[str, ...]:
        """Every ULD code in the plan, in position order."""
        return tuple(a.uld for a in self.assignments if a.uld)

    @property
    def positions(self) -> tuple[str, ...]:
        """Every position used, in the order they were assigned."""
        return tuple(a.position for a in self.assignments)

    @property
    def destinations(self) -> tuple[str, ...]:
        """Every offload point in the plan, once each."""
        return tuple(sorted({a.destination for a in self.assignments if a.destination}))

    @property
    def empty(self) -> bool:
        """A plan with nothing assigned yet."""
        return not self.assignments

    def holds(self, position: str) -> bool:
        """Whether a position has been given something."""
        return position.strip().upper() in set(self.positions)

    def at(self, position: str) -> Assignment:
        """What is in one position."""
        wanted = position.strip().upper()
        for assignment in self.assignments:
            if assignment.position == wanted:
                return assignment
        raise NotFoundError(f"nothing is planned for position {wanted}")

    def carrying(self, uld: str) -> Assignment:
        """Which position a device is in."""
        wanted = parse_uld(uld).formatted()
        for assignment in self.assignments:
            if assignment.uld == wanted:
                return assignment
        raise NotFoundError(f"{wanted} is not in this plan")

    def assign(self, assignment: Assignment) -> LoadPlan:
        """Put something in a position, refusing one that is taken."""
        if self.holds(assignment.position):
            raise RuleError(
                f"position {assignment.position} already holds "
                f"{self.at(assignment.position).uld or BULK}"
            )
        return replace(self, assignments=(*self.assignments, assignment))

    def release(self, position: str) -> LoadPlan:
        """Take whatever is in a position out of the plan."""
        wanted = position.strip().upper()
        if not self.holds(wanted):
            raise NotFoundError(f"nothing is planned for position {wanted}")
        kept = tuple(a for a in self.assignments if a.position != wanted)
        return replace(self, assignments=kept)

    def move(self, position: str, to: str) -> LoadPlan:
        """Move whatever is in one position into another.

        The device and the offload point travel with the load, which is the
        whole reason this is not a release and an assign. Doing it in two steps
        means retyping both, and retyping the destination is how a pallet ends
        up planned for the wrong station.
        """
        held = self.at(position)
        wanted = to.strip().upper()
        if self.holds(wanted):
            raise RuleError(f"position {wanted} already holds {self.at(wanted).uld or BULK}")
        moved = replace(held, position=wanted)
        kept = tuple(
            moved if entry.position == held.position else entry for entry in self.assignments
        )
        return replace(self, assignments=kept)

    def reissued(self) -> LoadPlan:
        """The same plan at the next edition, which is what a change makes."""
        return replace(self, edition=self.edition + 1)
