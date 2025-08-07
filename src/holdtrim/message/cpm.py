"""The container and pallet message.

Where the LDM says how much is on board, the CPM says exactly which device is
in which position. The station at the other end plans its unloading order from
it, and its ULD control department reconciles its stock against it, so it is
the message that gets read most carefully and complained about most loudly.

    CPM
    QH412/12.OY-JAF.BLL
    -LGG
    .11P/PMC12345QH/2000/LGG
    .51/BULK/300/LGG
    NIL 21P

Positions with nothing in them are listed rather than left out. A missing
position and an empty position look the same in a message that only lists what
is loaded, and the difference matters when somebody is looking for a device
that should have been on the aeroplane.
"""

from __future__ import annotations

from holdtrim.message.teletype import URGENT, Message, wrap
from holdtrim.sheet.loadsheet import Loadsheet

BULK_MARKER = "BULK"
NIL = "NIL"


def flight_line(sheet: Loadsheet) -> str:
    """Flight, day, registration and the station it is leaving."""
    return f"{sheet.sector.reference}.{sheet.tail.registration}.{sheet.sector.origin}"


def position_line(sheet: Loadsheet, position: str) -> str:
    """One loaded position: what is in it, what it weighs, where it goes."""
    assignment = sheet.plan.at(position)
    what = assignment.uld if assignment.uld else BULK_MARKER
    where = assignment.destination or sheet.sector.destination
    return f".{assignment.position}/{what}/{assignment.weight}/{where}"


def empty_positions(sheet: Loadsheet) -> tuple[str, ...]:
    """Every position on the type that this flight is not using."""
    return tuple(
        position.code
        for position in sheet.kind.layout.by_arm()
        if not sheet.plan.holds(position.code)
    )


def body(sheet: Loadsheet) -> tuple[str, ...]:
    """Every line under the type."""
    lines = [flight_line(sheet)]
    for destination in sorted(sheet.by_destination):
        lines.append(f"-{destination}")
        for assignment in sheet.plan.assignments:
            where = assignment.destination or sheet.sector.destination
            if where == destination:
                lines.append(position_line(sheet, assignment.position))
    empty = empty_positions(sheet)
    if empty:
        lines.extend(wrap(f"{NIL} {' '.join(empty)}"))
    if not sheet.plan.assignments:
        lines.append(f"-{sheet.sector.destination}")
    return tuple(lines)


def build(
    sheet: Loadsheet,
    *,
    addresses: tuple[str, ...],
    origin: str,
    filed: str,
    priority: str = URGENT,
) -> Message:
    """The whole CPM, envelope and all."""
    return Message(
        kind="CPM",
        addresses=addresses,
        origin=origin,
        filed=filed,
        body=body(sheet),
        priority=priority,
    )
