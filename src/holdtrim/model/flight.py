"""One flight, on one day, with one aeroplane.

Fuel is the part of this record that catches people out. Three figures are
recorded and they are not independent. Taxi fuel is burned before the aeroplane
is airborne, so it comes off the ramp weight and not the takeoff weight. Trip
fuel is burned between the two runways, so takeoff weight less trip fuel is the
landing weight. Takeoff fuel is what is in the tanks at the start of the roll,
and it has to be more than the trip fuel or the flight does not arrive.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from holdtrim.errors import DataError
from holdtrim.ids import Flight, parse_registration, parse_station
from holdtrim.units import to_kilos

PLANNED = "planned"
CLOSED = "closed"
DEPARTED = "departed"
CANCELLED = "cancelled"
STATUSES = (PLANNED, CLOSED, DEPARTED, CANCELLED)

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


@dataclass(frozen=True)
class Sector:
    """A flight as the office works it: a designator, a day and an aeroplane."""

    designator: Flight
    day: date
    registration: str
    origin: str
    destination: str
    taxi_fuel: int
    trip_fuel: int
    takeoff_fuel: int
    crew: int = 2
    freighter: bool = True
    status: str = PLANNED

    def __post_init__(self) -> None:
        object.__setattr__(self, "registration", parse_registration(self.registration))
        object.__setattr__(self, "origin", parse_station(self.origin))
        object.__setattr__(self, "destination", parse_station(self.destination))
        if self.origin == self.destination:
            raise DataError(f"{self.reference} goes from {self.origin} to itself")
        for name in ("taxi_fuel", "trip_fuel", "takeoff_fuel"):
            object.__setattr__(
                self, name, to_kilos(getattr(self, name), what=name.replace("_", " "))
            )
        if self.takeoff_fuel < self.trip_fuel:
            raise DataError(
                f"{self.reference} carries {self.takeoff_fuel} kg of fuel and the trip "
                f"burns {self.trip_fuel} kg"
            )
        if self.crew <= 0:
            raise DataError(f"{self.reference} has no crew on it")
        status = self.status.strip().lower()
        if status not in STATUSES:
            raise DataError(f"{self.reference} is in no status this build knows: {status}")
        object.__setattr__(self, "status", status)

    @property
    def reference(self) -> str:
        """The way a message names the flight: designator, then day of month."""
        return f"{self.designator}/{self.day.day:02d}"

    @property
    def key(self) -> str:
        """The way the office files it, unique across a season."""
        return f"{self.designator}/{self.day.isoformat()}"

    @property
    def teletype_day(self) -> str:
        """The day written the way a teletype message writes one."""
        return f"{self.day.day:02d}{MONTHS[self.day.month - 1]}"

    @property
    def route(self) -> str:
        """Where it goes, the way a manifest writes it."""
        return f"{self.origin}{self.destination}"

    @property
    def landing_fuel(self) -> int:
        """What is left in the tanks when it lands."""
        return self.takeoff_fuel - self.trip_fuel

    @property
    def block_fuel(self) -> int:
        """What goes in on the stand, taxi burn included."""
        return self.takeoff_fuel + self.taxi_fuel

    @property
    def open(self) -> bool:
        """Whether the load can still be changed."""
        return self.status == PLANNED

    @property
    def takes_cargo_aircraft_only(self) -> bool:
        """A freighter may carry what a passenger aeroplane may not."""
        return self.freighter

    def describe(self) -> str:
        """One line for a day's listing."""
        return (
            f"{self.reference} {self.route} {self.registration} "
            f"fuel {self.takeoff_fuel}/{self.trip_fuel} ({self.status})"
        )
