"""The load distribution message.

The LDM tells the down route station what is on the aeroplane and roughly
where, so that they can plan the offload before it lands. It is terse because
it was designed to be, and the terseness is load bearing: every full stop in it
separates one field from the next.

    LDM
    QH412/12.OY-JAF.7/0
    -LGG.0/0/0.T2300.2/2000.5/300
    SI PMC12345QH IN 11P

The second line is the flight, the day of the month, the registration, the crew
complement and the version. Each line after it is one offload point: the
station, the passenger figures, the total weight, and then one field per hold
with the weight in it. This is a freighter operation so the passenger figures
are zeroes, and they are printed rather than left out because a receiving
system that expects three numbers will not read a line that has none.
"""

from __future__ import annotations

from holdtrim.message.teletype import URGENT, Message, wrap
from holdtrim.sheet.loadsheet import Loadsheet

HOLD_NUMBERS = {"FWD": "1", "MAIN": "2", "AFT": "4", "BULK": "5"}
NO_PASSENGERS = "0/0/0"


def flight_line(sheet: Loadsheet) -> str:
    """Flight, day, registration, crew and version."""
    flight = sheet.sector
    return f"{flight.reference}.{sheet.tail.registration}.{flight.crew}/{sheet.edition - 1}"


def hold_field(compartment: str, weight: int) -> str:
    """One hold and what is in it."""
    return f"{HOLD_NUMBERS.get(compartment, '9')}/{weight}"


def destination_line(sheet: Loadsheet, destination: str) -> str:
    """One offload point, its total, and the holds it is spread across."""
    holds: dict[str, int] = {}
    total = 0
    for assignment in sheet.plan.assignments:
        where = assignment.destination or sheet.sector.destination
        if where != destination:
            continue
        compartment = sheet.kind.layout.position(assignment.position).compartment
        holds[compartment] = holds.get(compartment, 0) + assignment.weight
        total += assignment.weight
    fields = [
        hold_field(compartment, weight)
        for compartment, weight in sorted(
            holds.items(), key=lambda pair: HOLD_NUMBERS.get(pair[0], "9")
        )
    ]
    return ".".join([f"-{destination}", NO_PASSENGERS, f"T{total}", *fields])


def supplementary(sheet: Loadsheet) -> tuple[str, ...]:
    """The free text at the end, which is where a device gets named."""
    notes = [
        f"{assignment.uld} IN {assignment.position}"
        for assignment in sheet.plan.assignments
        if assignment.uld
    ]
    if not sheet.changes.empty:
        notes.append(f"LMC {sheet.changes.net} KG")
    if not notes:
        return ()
    return wrap("SI " + " ".join(notes))


def body(sheet: Loadsheet) -> tuple[str, ...]:
    """Every line of the message under the type."""
    lines = [flight_line(sheet)]
    for destination in sorted(sheet.by_destination):
        lines.append(destination_line(sheet, destination))
    lines.extend(supplementary(sheet))
    return tuple(lines)


def build(
    sheet: Loadsheet,
    *,
    addresses: tuple[str, ...],
    origin: str,
    filed: str,
    priority: str = URGENT,
) -> Message:
    """The whole LDM, envelope and all."""
    return Message(
        kind="LDM",
        addresses=addresses,
        origin=origin,
        filed=filed,
        body=body(sheet),
        priority=priority,
    )
