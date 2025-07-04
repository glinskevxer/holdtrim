"""Screening a planned load for dangerous goods problems.

Three different things are being checked here and they are easy to run
together, so they are kept apart.

Whether the shipment may be on this aeroplane at all is a question about the
flight: a cargo aircraft only shipment on a passenger flight is a refusal
however it is loaded.

Whether two shipments may be next to each other is a question about the
positions. Two classes that segregate may not share a position, and where they
are not in devices they may not be in neighbouring positions either.

How much radioactive material is on board is a question about the whole
aeroplane, because the transport indices add up across every position.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.danger.table import class_name, conflicts, is_explosive_exception, separation_for
from holdtrim.findings import STOP, WATCH, Finding
from holdtrim.model.danger import DangerousGoods
from holdtrim.model.hold import HoldLayout

CARGO_AIRCRAFT_ONLY = "cargo aircraft only"
SEGREGATION = "segregation"
SEPARATION = "separation"
RADIOACTIVE = "radioactive"
EXPLOSIVE = "explosive"

MAX_TRANSPORT_INDEX_PER_AIRCRAFT = Decimal("50.0")
MAX_TRANSPORT_INDEX_PER_POSITION = Decimal("50.0")


@dataclass(frozen=True)
class Placement:
    """One waybill's dangerous goods, in the position it is planned for."""

    position: str
    awb: str
    entries: tuple[DangerousGoods, ...]
    in_device: bool = True

    @property
    def classes(self) -> tuple[str, ...]:
        """Every class and subsidiary risk in this placement."""
        risks: set[str] = set()
        for entry in self.entries:
            risks.update(entry.all_risks)
        return tuple(sorted(risks))

    @property
    def transport_index(self) -> Decimal:
        """The radioactive transport index of everything in this placement."""
        total = Decimal("0.0")
        for entry in self.entries:
            if entry.transport_index is not None:
                total += entry.transport_index * entry.packages
        return total

    @property
    def cargo_aircraft_only(self) -> bool:
        """Whether anything here bars a passenger flight."""
        return any(entry.cargo_aircraft_only for entry in self.entries)

    @property
    def explosive(self) -> bool:
        """Whether anything here is class 1 other than the 1.4S exception."""
        return any(
            entry.explosive and not is_explosive_exception(entry.hazard_class)
            for entry in self.entries
        )


def on_this_aeroplane(placements: tuple[Placement, ...], *, freighter: bool) -> tuple[Finding, ...]:
    """Whether every shipment may be on this kind of flight."""
    if freighter:
        return ()
    return tuple(
        Finding(
            check=CARGO_AIRCRAFT_ONLY,
            where=placement.position,
            detail=f"waybill {placement.awb} may only fly on a freighter",
        )
        for placement in placements
        if placement.cargo_aircraft_only
    )


def within_positions(placements: tuple[Placement, ...]) -> tuple[Finding, ...]:
    """Classes that may not share a position."""
    by_position: dict[str, list[Placement]] = {}
    for placement in placements:
        by_position.setdefault(placement.position, []).append(placement)
    found = []
    for position, held in sorted(by_position.items()):
        risks: set[str] = set()
        for placement in held:
            risks.update(placement.classes)
        for first, second in conflicts(risks):
            found.append(
                Finding(
                    check=SEGREGATION,
                    where=position,
                    detail=(
                        f"{class_name(first)} and {class_name(second)} may not share a position"
                    ),
                )
            )
    return tuple(found)


def between_positions(placements: tuple[Placement, ...], layout: HoldLayout) -> tuple[Finding, ...]:
    """Classes that may not be in neighbouring positions when loose."""
    order = [position.code for position in layout.by_arm()]
    loose = [placement for placement in placements if not placement.in_device]
    found = []
    for i, first in enumerate(loose):
        for second in loose[i + 1 :]:
            if first.position == second.position:
                continue
            if not _neighbours(order, first.position, second.position):
                continue
            for left, right in conflicts({*first.classes, *second.classes}):
                found.append(
                    Finding(
                        check=SEPARATION,
                        where=f"{first.position}/{second.position}",
                        detail=(
                            f"{class_name(left)} and {class_name(right)} are loose in "
                            "neighbouring positions"
                        ),
                    )
                )
    return tuple(found)


def _neighbours(order: list[str], first: str, second: str) -> bool:
    if first not in order or second not in order:
        return False
    return abs(order.index(first) - order.index(second)) == 1


def radioactivity(placements: tuple[Placement, ...]) -> tuple[Finding, ...]:
    """The transport index per position and across the whole aeroplane."""
    found = []
    total = Decimal("0.0")
    for placement in sorted(placements, key=lambda held: held.position):
        index = placement.transport_index
        total += index
        if index > MAX_TRANSPORT_INDEX_PER_POSITION:
            found.append(
                Finding(
                    check=RADIOACTIVE,
                    where=placement.position,
                    detail=(
                        f"transport index {index} is over the {MAX_TRANSPORT_INDEX_PER_POSITION} "
                        "allowed in one position"
                    ),
                )
            )
        elif index > 0:
            found.append(
                Finding(
                    check=RADIOACTIVE,
                    where=placement.position,
                    detail=(
                        f"transport index {index} needs {separation_for(index)} m of separation"
                    ),
                    severity=WATCH,
                )
            )
    if total > MAX_TRANSPORT_INDEX_PER_AIRCRAFT:
        found.append(
            Finding(
                check=RADIOACTIVE,
                where="aircraft",
                detail=(
                    f"transport index {total} is over the "
                    f"{MAX_TRANSPORT_INDEX_PER_AIRCRAFT} allowed on one aeroplane"
                ),
            )
        )
    return tuple(found)


def explosives(placements: tuple[Placement, ...]) -> tuple[Finding, ...]:
    """Explosives have a position to themselves, 1.4S apart."""
    found = []
    for placement in sorted(placements, key=lambda held: held.position):
        if not placement.explosive:
            continue
        sharing = [
            other
            for other in placements
            if other.position == placement.position and other.awb != placement.awb
        ]
        if sharing:
            found.append(
                Finding(
                    check=EXPLOSIVE,
                    where=placement.position,
                    detail=(
                        f"waybill {placement.awb} is explosive and shares its position "
                        f"with {len(sharing)} other consignment(s)"
                    ),
                )
            )
    return tuple(found)


def screen(
    placements: tuple[Placement, ...], layout: HoldLayout, *, freighter: bool = True
) -> tuple[Finding, ...]:
    """Every dangerous goods check, all of them run."""
    return (
        *on_this_aeroplane(placements, freighter=freighter),
        *within_positions(placements),
        *between_positions(placements, layout),
        *radioactivity(placements),
        *explosives(placements),
    )


def acceptable(findings: tuple[Finding, ...]) -> bool:
    """Whether nothing found stops the flight."""
    return all(finding.severity != STOP for finding in findings)
