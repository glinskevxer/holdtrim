"""The weight and balance calculation itself.

An aeroplane is checked at three weights and they are worked out in this order,
because each one is built on the one before.

Zero fuel weight is the dry operating weight plus everything loaded. It is the
weight the airframe carries as bending load, and it is the only one of the
three the load controller can change.

Takeoff weight is zero fuel weight plus the fuel in the tanks at the start of
the roll. Landing weight is takeoff weight less what the trip burns. Ramp
weight is takeoff weight plus the taxi fuel, and it is checked against a
different limit because the aeroplane is still on its wheels.

The index follows the same chain. Every load contributes at its position's arm,
and the fuel contributes off the fuel table rather than an arm.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.balance.index import Contribution, percent_mac, total_index
from holdtrim.errors import DataError
from holdtrim.model.aircraft import AircraftType
from holdtrim.model.position import Position
from holdtrim.model.tail import Tail
from holdtrim.units import to_index

ZERO_FUEL = "zero fuel"
TAKEOFF = "takeoff"
LANDING = "landing"


@dataclass(frozen=True)
class LoadedPosition:
    """A weight in a position, and what it is."""

    position: Position
    weight: int
    label: str = ""

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise DataError(f"position {self.position.code} cannot hold a negative weight")

    @property
    def contribution(self) -> Contribution:
        """The load as the index arithmetic wants it."""
        return Contribution(label=self.position.code, weight=self.weight, arm=self.position.arm)

    def describe(self) -> str:
        """One line for the loading instruction."""
        what = self.label if self.label else "bulk"
        return f"{self.position.code} {what} {self.weight} kg"


@dataclass(frozen=True)
class Condition:
    """A weight and an index at one point in the flight."""

    name: str
    weight: int
    index: Decimal

    def percent_mac(self, kind: AircraftType) -> Decimal:
        """Where the centre of gravity sits, as a percentage of chord."""
        return percent_mac(self.weight, self.index, kind.geometry)


@dataclass(frozen=True)
class Balance:
    """One flight's figures, from the dry aeroplane to the landing weight."""

    kind: AircraftType
    tail: Tail
    loads: tuple[LoadedPosition, ...]
    taxi_fuel: int
    trip_fuel: int
    takeoff_fuel: int

    @property
    def payload(self) -> int:
        """Everything loaded, in kilograms."""
        return sum(load.weight for load in self.loads)

    @property
    def loaded_positions(self) -> dict[str, int]:
        """What each position is carrying, for the limit checks."""
        carried: dict[str, int] = {}
        for load in self.loads:
            carried[load.position.code] = carried.get(load.position.code, 0) + load.weight
        return carried

    @property
    def zero_fuel(self) -> Condition:
        """Dry operating weight plus payload, and the index that goes with it."""
        index = total_index(
            tuple(load.contribution for load in self.loads),
            self.kind.geometry,
            base=self.tail.dry_operating_index,
        )
        return Condition(
            name=ZERO_FUEL,
            weight=self.tail.dry_operating_weight + self.payload,
            index=index,
        )

    @property
    def takeoff(self) -> Condition:
        """Zero fuel plus the fuel that is in the tanks at the start of the roll."""
        correction = self.kind.fuel.index_at(self.takeoff_fuel)
        return Condition(
            name=TAKEOFF,
            weight=self.zero_fuel.weight + self.takeoff_fuel,
            index=to_index(self.zero_fuel.index + correction),
        )

    @property
    def landing(self) -> Condition:
        """Takeoff less what the trip burns, at the index the remaining fuel gives."""
        remaining = self.takeoff_fuel - self.trip_fuel
        correction = self.kind.fuel.index_at(remaining)
        return Condition(
            name=LANDING,
            weight=self.zero_fuel.weight + remaining,
            index=to_index(self.zero_fuel.index + correction),
        )

    @property
    def ramp_weight(self) -> int:
        """What the aeroplane weighs on the stand with the taxi fuel on board."""
        return self.takeoff.weight + self.taxi_fuel

    @property
    def conditions(self) -> tuple[Condition, ...]:
        """The three weights the envelope is read at, in order."""
        return (self.zero_fuel, self.takeoff, self.landing)

    def condition(self, name: str) -> Condition:
        """One of the three by name."""
        wanted = name.strip().lower()
        for condition in self.conditions:
            if condition.name == wanted:
                return condition
        raise DataError(f"{wanted} is not one of the three weights")

    @property
    def underload_to_zero_fuel(self) -> int:
        """How much more payload the zero fuel limit would allow."""
        return self.kind.limits.max_zero_fuel - self.zero_fuel.weight

    @property
    def underload_to_takeoff(self) -> int:
        """How much more payload the takeoff limit would allow."""
        return self.kind.limits.max_takeoff - self.takeoff.weight

    @property
    def underload_to_landing(self) -> int:
        """How much more payload the landing limit would allow."""
        return self.kind.limits.max_landing - self.landing.weight

    @property
    def underload(self) -> int:
        """The smallest of the three, which is what the office can actually sell."""
        return min(
            self.underload_to_zero_fuel,
            self.underload_to_takeoff,
            self.underload_to_landing,
        )

    @property
    def limiting_weight(self) -> str:
        """Which of the three limits is the one biting."""
        margins = {
            ZERO_FUEL: self.underload_to_zero_fuel,
            TAKEOFF: self.underload_to_takeoff,
            LANDING: self.underload_to_landing,
        }
        return min(margins, key=lambda name: margins[name])


def load_positions(kind: AircraftType, weights: dict[str, int]) -> tuple[LoadedPosition, ...]:
    """Turn a plain mapping of position code to weight into loads."""
    return tuple(
        LoadedPosition(position=kind.layout.position(code), weight=weight)
        for code, weight in weights.items()
    )
