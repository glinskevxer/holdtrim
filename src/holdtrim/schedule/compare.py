"""Two weight schedules, and what is different about them.

A schedule is reissued when an aeroplane is modified or when the manufacturer
publishes a revision, and the new one arrives as a whole document rather than
as a list of what changed. Somebody then has to work out what moved, because
the answer decides whether every load plan built on the old one is still valid.

Doing that by eye across forty positions is how a changed running load gets
missed. This does it field by field and says what moved, in the words the
schedule uses.
"""

from __future__ import annotations

from dataclasses import dataclass

from holdtrim.model.aircraft import AircraftType

LIMITS = "structural limit"
GEOMETRY = "geometry"
POSITION = "position"
ENVELOPE = "envelope"
TABLE = "table"


@dataclass(frozen=True)
class Change:
    """One field that is not the same in both schedules."""

    about: str
    field: str
    was: str
    now: str

    def describe(self) -> str:
        """One line for the comparison."""
        return f"{self.about} {self.field}: {self.was} became {self.now}"


def _limits(old: AircraftType, new: AircraftType) -> list[Change]:
    was = old.limits.as_dict()
    now = new.limits.as_dict()
    return [
        Change(about=LIMITS, field=name, was=str(was[name]), now=str(now[name]))
        for name in was
        if was[name] != now[name]
    ]


def _geometry(old: AircraftType, new: AircraftType) -> list[Change]:
    fields = ("reference_arm", "lemac", "mac_length", "index_constant", "index_reference")
    found = []
    for name in fields:
        before = getattr(old.geometry, name)
        after = getattr(new.geometry, name)
        if before != after:
            found.append(Change(about=GEOMETRY, field=name, was=str(before), now=str(after)))
    return found


def _positions(old: AircraftType, new: AircraftType) -> list[Change]:
    fields = ("arm", "max_weight", "length", "width", "max_running_load", "max_area_load")
    found = []
    before = {position.code: position for position in old.layout.positions}
    after = {position.code: position for position in new.layout.positions}
    for code in sorted(set(before) - set(after)):
        found.append(Change(about=POSITION, field=code, was="present", now="gone"))
    for code in sorted(set(after) - set(before)):
        found.append(Change(about=POSITION, field=code, was="not there", now="added"))
    for code in sorted(set(before) & set(after)):
        for name in fields:
            was = getattr(before[code], name)
            now = getattr(after[code], name)
            if was != now:
                found.append(
                    Change(about=POSITION, field=f"{code} {name}", was=str(was), now=str(now))
                )
    return found


def _envelopes(old: AircraftType, new: AircraftType) -> list[Change]:
    found = []
    before = {shape.name: shape for shape in old.envelopes}
    after = {shape.name: shape for shape in new.envelopes}
    for name in sorted(set(before) | set(after)):
        if name not in before or name not in after:
            found.append(
                Change(
                    about=ENVELOPE,
                    field=name,
                    was="present" if name in before else "not there",
                    now="gone" if name not in after else "added",
                )
            )
        elif before[name].points != after[name].points:
            found.append(
                Change(
                    about=ENVELOPE,
                    field=name,
                    was=f"{len(before[name].points)} breakpoint(s)",
                    now=f"{len(after[name].points)} breakpoint(s), and they are not the same",
                )
            )
    return found


def _tables(old: AircraftType, new: AircraftType) -> list[Change]:
    found = []
    if old.fuel.points != new.fuel.points:
        found.append(Change(about=TABLE, field="fuel index", was="as published", now="changed"))
    if old.trim.points != new.trim.points:
        found.append(Change(about=TABLE, field="trim", was="as published", now="changed"))
    return found


def differences(old: AircraftType, new: AircraftType) -> tuple[Change, ...]:
    """Everything that is not the same in the two schedules."""
    return (
        *_limits(old, new),
        *_geometry(old, new),
        *_positions(old, new),
        *_envelopes(old, new),
        *_tables(old, new),
    )


def same(old: AircraftType, new: AircraftType) -> bool:
    """Whether the two schedules say the same thing."""
    return not differences(old, new)
