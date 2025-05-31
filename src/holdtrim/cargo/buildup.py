"""Building consignments into a device.

A build up is the point where paperwork becomes weight. Up to here a
consignment is a row with a figure on it. Once it is in a ULD there is a gross
weight the position limits are going to be checked against, and it is the tare
plus everything inside.

The rules that stop a build up happening are few and they are all about what
comes off at the other end. One destination per device, because a device is
opened once. Nothing stacked on something that says do not stack it. And never
past the device's own maximum gross, which is a certification limit and not a
target.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.cargo import handling
from holdtrim.errors import RuleError, StateError
from holdtrim.model.consignment import Consignment
from holdtrim.model.uld import Uld


@dataclass(frozen=True)
class BuildUp:
    """One device and everything that has been put in it."""

    uld: Uld
    consignments: tuple[Consignment, ...] = ()

    @property
    def contents_weight(self) -> int:
        """What is inside, tare not counted."""
        return sum(consignment.gross_weight for consignment in self.consignments)

    @property
    def gross_weight(self) -> int:
        """What the ramp will read off the scales."""
        return self.uld.gross_at(self.contents_weight)

    @property
    def pieces(self) -> int:
        """How many pieces are in it."""
        return sum(consignment.pieces for consignment in self.consignments)

    @property
    def volume(self) -> Decimal:
        """The volume taken up, as measured at acceptance."""
        return sum((consignment.volume for consignment in self.consignments), Decimal("0.000"))

    @property
    def destination(self) -> str:
        """Where the device is opened, empty while it is still empty."""
        if not self.consignments:
            return ""
        return self.consignments[0].destination

    @property
    def handling_codes(self) -> tuple[str, ...]:
        """Every code on everything inside, once each."""
        codes: set[str] = set()
        for consignment in self.consignments:
            codes.update(consignment.handling)
        return tuple(sorted(codes))

    @property
    def dangerous(self) -> bool:
        """Whether anything in the device is dangerous goods."""
        return bool(handling.dangerous(self.handling_codes))

    @property
    def cargo_aircraft_only(self) -> bool:
        """Whether the device may only fly on a freighter."""
        return handling.cargo_aircraft_only(self.handling_codes)

    @property
    def stackable(self) -> bool:
        """Whether anything may be put on top of the device."""
        return handling.stackable(self.handling_codes)

    @property
    def empty(self) -> bool:
        """A device with nothing in it, which still weighs its tare."""
        return not self.consignments

    def carries(self, awb: str) -> bool:
        """Whether a waybill is in this device."""
        wanted = awb.strip().replace("-", "")
        return any(consignment.awb.plain() == wanted for consignment in self.consignments)

    def describe(self) -> str:
        """One line for the build up sheet."""
        where = self.destination if self.destination else "empty"
        codes = " ".join(self.handling_codes)
        line = f"{self.uld.code} {where} {self.pieces} pieces {self.gross_weight} kg"
        return f"{line} {codes}".rstrip()


def build(device: Uld, consignments: tuple[Consignment, ...] = ()) -> BuildUp:
    """Put consignments in a device, refusing anything that must not be done."""
    if not device.loadable:
        raise StateError(f"{device.code} is {device.condition} and cannot be built up")
    made = BuildUp(uld=device, consignments=())
    for consignment in consignments:
        made = put(made, consignment)
    return made


def put(made: BuildUp, consignment: Consignment) -> BuildUp:
    """Add one consignment to a build up."""
    if made.carries(consignment.awb.plain()):
        raise RuleError(f"waybill {consignment.awb} is already in {made.uld.code}")
    if made.destination and consignment.destination != made.destination:
        raise RuleError(
            f"{made.uld.code} is built for {made.destination} and waybill "
            f"{consignment.awb} is for {consignment.destination}"
        )
    if made.consignments and not made.stackable:
        raise RuleError(
            f"{made.uld.code} holds {' '.join(made.handling_codes)} and nothing "
            "may be loaded on top of it"
        )
    if made.consignments and not handling.stackable(consignment.handling):
        raise RuleError(
            f"waybill {consignment.awb} may not be stacked and {made.uld.code} "
            "already holds something"
        )
    over = made.uld.over_gross_by(made.contents_weight + consignment.gross_weight)
    if over:
        raise RuleError(
            f"{made.uld.code} would be {over} kg over its maximum gross of {made.uld.max_gross} kg"
        )
    return BuildUp(uld=made.uld, consignments=(*made.consignments, consignment))
