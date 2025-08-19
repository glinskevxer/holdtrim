"""The notification to captain.

This is the one document on a flight that exists purely so that somebody can
act on it in an emergency. The commander is told what dangerous goods are on
board and where they are, so that if there is a fire in a hold they know
whether they are dealing with paint or with an oxidiser.

That purpose sets the layout. Position comes before quantity, because in the
air the position is the question. Radioactive material is listed separately
with its transport index, because the handling is different in kind and not
just in degree. Anything that is not dangerous goods but which the crew still
have to know about, live animals in particular, goes underneath in its own
section.

The commander signs it and a copy stays on the ground. Both of those matter
after an incident, and neither of them works if the document is missing a line.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.danger.screen import Placement
from holdtrim.errors import RuleError
from holdtrim.model.flight import Sector

WIDTH = 92
RULE = "-" * WIDTH
LIVE_ANIMALS = "AVI"


@dataclass(frozen=True)
class Notoc:
    """One flight's notification, as data rather than as paper."""

    sector: Sector
    placements: tuple[Placement, ...]
    prepared_by: str
    live_animals: tuple[tuple[str, str, int], ...] = ()

    @property
    def dangerous(self) -> tuple[Placement, ...]:
        """The placements that carry dangerous goods, in position order."""
        return tuple(
            sorted(
                (held for held in self.placements if held.entries),
                key=lambda held: (held.position, held.awb),
            )
        )

    @property
    def radioactive(self) -> tuple[Placement, ...]:
        """The placements that carry class 7."""
        return tuple(held for held in self.dangerous if held.transport_index > 0)

    @property
    def total_transport_index(self) -> Decimal:
        """Every transport index on board, added up."""
        total = Decimal("0.0")
        for held in self.radioactive:
            total += held.transport_index
        return total

    @property
    def cargo_aircraft_only(self) -> tuple[Placement, ...]:
        """The placements that may only travel on a freighter."""
        return tuple(held for held in self.dangerous if held.cargo_aircraft_only)

    @property
    def needed(self) -> bool:
        """Whether the commander has to be handed anything at all."""
        return bool(self.dangerous or self.live_animals)

    def issue(self) -> Notoc:
        """Confirm the notice, refusing one that nobody prepared."""
        if not self.prepared_by.strip():
            raise RuleError("a notification to captain has to say who prepared it")
        return self


def header(notice: Notoc) -> list[str]:
    """Which flight, which aeroplane, and who filled it in."""
    flight = notice.sector
    return [
        "NOTIFICATION TO CAPTAIN".center(WIDTH),
        RULE,
        f"flight {flight.reference}   aircraft {flight.registration}   "
        f"{flight.origin} to {flight.destination}   date {flight.day.isoformat()}",
        f"prepared by {notice.prepared_by}",
        RULE,
    ]


def goods(notice: Notoc) -> list[str]:
    """One line per dangerous goods entry, position first."""
    if not notice.dangerous:
        return ["no dangerous goods on board"]
    lines = [
        f"{'position':<10}{'waybill':<14}{'UN':<7}{'class':<8}{'PG':<4}"
        f"{'pkgs':<6}{'quantity':<14}{'CAO':<5}shipping name"
    ]
    for held in notice.dangerous:
        for entry in held.entries:
            quantity = f"{entry.total_quantity} {entry.unit}"
            lines.append(
                f"{held.position:<10}{held.awb:<14}{entry.un_number:<7}"
                f"{entry.hazard_class:<8}{entry.packing_group or '-':<4}"
                f"{entry.packages:<6}{quantity:<14}"
                f"{'yes' if entry.cargo_aircraft_only else 'no':<5}"
                f"{entry.proper_shipping_name}"
            )
    return lines


def radioactive(notice: Notoc) -> list[str]:
    """The class 7 section, with the transport indices."""
    if not notice.radioactive:
        return []
    lines = [RULE, "RADIOACTIVE MATERIAL".center(WIDTH), RULE]
    for held in notice.radioactive:
        lines.append(f"{held.position:<10}{held.awb:<14}transport index {held.transport_index}")
    lines.append(f"{'total':<10}{'':<14}transport index {notice.total_transport_index}")
    return lines


def other(notice: Notoc) -> list[str]:
    """Everything the crew have to know about that is not dangerous goods."""
    if not notice.live_animals:
        return []
    lines = [RULE, "OTHER SPECIAL LOAD".center(WIDTH), RULE]
    for position, awb, pieces in notice.live_animals:
        lines.append(f"{position:<10}{awb:<14}{LIVE_ANIMALS} {pieces} piece(s)")
    return lines


def footer() -> list[str]:
    """The signature block, which is the point of the whole document."""
    return [
        RULE,
        "commander signature ...........................   time ..........",
        RULE,
    ]


def render(notice: Notoc) -> str:
    """The whole notice as one block of text."""
    lines = [
        *header(notice),
        *goods(notice),
        *radioactive(notice),
        *other(notice),
        *footer(),
    ]
    return "\n".join(lines) + "\n"
