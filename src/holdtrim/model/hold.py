"""The layout of the holds, and the limits that span more than one position.

Position limits are not the whole story. The loading manual also prints
combined limits: 11 and 12 together may not exceed a figure that is less than
the sum of the two, because the floor beam between them carries both. Those
are the limits that get missed, because each position on its own looks legal.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.errors import DataError, NotFoundError
from holdtrim.model.position import COMPARTMENTS, Position
from holdtrim.units import to_kilos


@dataclass(frozen=True)
class CumulativeLimit:
    """A weight limit shared by a run of positions."""

    label: str
    positions: tuple[str, ...]
    max_weight: int

    def __post_init__(self) -> None:
        label = self.label.strip()
        if not label:
            raise DataError("a cumulative limit needs a label")
        object.__setattr__(self, "label", label)
        codes = tuple(code.strip().upper() for code in self.positions)
        if len(codes) < 2:
            raise DataError(f"cumulative limit {label} spans fewer than two positions")
        if len(set(codes)) != len(codes):
            raise DataError(f"cumulative limit {label} names a position twice")
        object.__setattr__(self, "positions", codes)
        object.__setattr__(self, "max_weight", to_kilos(self.max_weight, what="cumulative limit"))
        if self.max_weight <= 0:
            raise DataError(f"cumulative limit {label} has no weight")

    def covers(self, code: str) -> bool:
        """Whether this limit watches that position."""
        return code.strip().upper() in self.positions

    def over_by(self, loaded: dict[str, int]) -> int:
        """How far past the shared limit a set of loaded positions sits."""
        total = sum(loaded.get(code, 0) for code in self.positions)
        return max(0, total - self.max_weight)


@dataclass(frozen=True)
class HoldLayout:
    """Every position on a type, and the limits that span them."""

    positions: tuple[Position, ...]
    cumulative: tuple[CumulativeLimit, ...] = ()

    def __post_init__(self) -> None:
        if not self.positions:
            raise DataError("a layout with no positions is not a layout")
        codes = [position.code for position in self.positions]
        if len(set(codes)) != len(codes):
            raise DataError("two positions share a code")
        known = set(codes)
        for limit in self.cumulative:
            missing = [code for code in limit.positions if code not in known]
            if missing:
                raise DataError(
                    f"cumulative limit {limit.label} names positions that are not "
                    f"in the layout: {', '.join(missing)}"
                )

    @property
    def codes(self) -> tuple[str, ...]:
        """Every position code, in the order the layout lists them."""
        return tuple(position.code for position in self.positions)

    @property
    def capacity(self) -> int:
        """The sum of the position limits, which the cumulative limits cut into."""
        return sum(position.max_weight for position in self.positions)

    def position(self, code: str) -> Position:
        """One position by code."""
        wanted = code.strip().upper()
        for position in self.positions:
            if position.code == wanted:
                return position
        raise NotFoundError(f"no position {wanted} in this layout")

    def has(self, code: str) -> bool:
        """Whether a code names a position here."""
        return code.strip().upper() in set(self.codes)

    def in_compartment(self, compartment: str) -> tuple[Position, ...]:
        """Every position in one compartment, in layout order."""
        wanted = compartment.strip().upper()
        if wanted not in COMPARTMENTS:
            raise DataError(f"no compartment called {wanted}")
        return tuple(p for p in self.positions if p.compartment == wanted)

    def by_arm(self) -> tuple[Position, ...]:
        """Every position front to back, which is the order a load is built in."""
        return tuple(sorted(self.positions, key=lambda p: (p.arm, p.code)))

    def limits_touching(self, code: str) -> tuple[CumulativeLimit, ...]:
        """Every cumulative limit that watches a position."""
        return tuple(limit for limit in self.cumulative if limit.covers(code))

    def arm_span(self) -> tuple[Decimal, Decimal]:
        """The forward-most and aft-most arms in the layout."""
        arms = [position.arm for position in self.positions]
        return min(arms), max(arms)

    def accepting(self, base: str) -> tuple[Position, ...]:
        """Every position that takes a ULD of that base size, front to back."""
        return tuple(p for p in self.by_arm() if p.accepts_base(base))
