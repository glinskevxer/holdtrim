"""The stabiliser trim setting that goes on the loadsheet.

The crew set the trim before the takeoff roll and they set it from the centre
of gravity, not from the weight. The schedule prints the relationship as a
table of percent chord against setting, and the setting is what the loadsheet
carries, so this is the last step of the calculation and the one the flight
deck actually reads.

Reading a setting outside the printed table is refused rather than
extrapolated. A trim table stops where the certified envelope stops, and a
number invented past the end of it is a number nobody has flown.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.errors import DataError, RuleError
from holdtrim.units import to_percent


@dataclass(frozen=True)
class TrimPoint:
    """One printed row: a centre of gravity and the setting for it."""

    percent_mac: Decimal
    setting: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "percent_mac", to_percent(self.percent_mac))
        object.__setattr__(self, "setting", to_percent(self.setting, what="trim setting"))


@dataclass(frozen=True)
class TrimTable:
    """The trim table off the schedule, read at any point it covers."""

    points: tuple[TrimPoint, ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise DataError("a trim table needs at least two rows")
        readings = [point.percent_mac for point in self.points]
        if readings != sorted(readings) or len(set(readings)) != len(readings):
            raise DataError("the trim table rows are not in order of percent chord")

    @property
    def forward_end(self) -> Decimal:
        """The most forward centre of gravity the table is printed for."""
        return self.points[0].percent_mac

    @property
    def aft_end(self) -> Decimal:
        """The most aft centre of gravity the table is printed for."""
        return self.points[-1].percent_mac

    def covers(self, percent_mac: Decimal) -> bool:
        """Whether the table says anything at that centre of gravity."""
        return self.forward_end <= percent_mac <= self.aft_end

    def setting_at(self, percent_mac: Decimal) -> Decimal:
        """The setting for a centre of gravity, interpolated between rows."""
        reading = to_percent(percent_mac)
        if not self.covers(reading):
            raise RuleError(
                f"{reading} percent chord is off the trim table, which runs "
                f"{self.forward_end} to {self.aft_end}"
            )
        below = self.points[0]
        for point in self.points:
            if point.percent_mac == reading:
                return point.setting
            if point.percent_mac < reading:
                below = point
            else:
                span = point.percent_mac - below.percent_mac
                along = (reading - below.percent_mac) / span
                return to_percent(
                    below.setting + (point.setting - below.setting) * along,
                    what="trim setting",
                )
        raise RuleError(f"{reading} percent chord fell off the trim table")  # pragma: no cover

    def rows(self) -> tuple[tuple[Decimal, Decimal], ...]:
        """The table as it is printed, for a report."""
        return tuple((point.percent_mac, point.setting) for point in self.points)
