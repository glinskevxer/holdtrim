"""A station: an airport this operation loads or unloads at.

Elevation is here because it decides the runway performance figures the crew
work from, and free storage days are here because they decide when a
consignment sitting in the shed starts costing the consignee money.
"""

from __future__ import annotations

from dataclasses import dataclass

from holdtrim.errors import DataError
from holdtrim.ids import parse_station

LOWEST_AIRFIELD_FEET = -1400
HIGHEST_AIRFIELD_FEET = 15000


@dataclass(frozen=True, order=True)
class Station:
    """One airport, as the load control office needs to know it."""

    code: str
    name: str
    elevation_feet: int
    handling_agent: str = ""
    free_storage_days: int = 2

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", parse_station(self.code))
        name = self.name.strip()
        if not name:
            raise DataError(f"station {self.code} has no name")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "handling_agent", self.handling_agent.strip())
        if not LOWEST_AIRFIELD_FEET <= self.elevation_feet <= HIGHEST_AIRFIELD_FEET:
            raise DataError(
                f"station {self.code} elevation {self.elevation_feet} ft is not an airfield"
            )
        if self.free_storage_days < 0:
            raise DataError(f"station {self.code} cannot have negative free storage days")

    @property
    def self_handled(self) -> bool:
        """True where the airline works its own ramp."""
        return self.handling_agent == ""

    def describe(self) -> str:
        """One line for a listing."""
        agent = self.handling_agent if self.handling_agent else "self handled"
        return f"{self.code} {self.name} ({agent})"
