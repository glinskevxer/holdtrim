"""Reading a load distribution message back.

Messages go out and messages come in. A down route station sends its own LDM
for the sector it is loading, and the office reads it to know what is arriving.
The same reader is worth having for our own messages, because comparing what
was sent against what the book says is the cheapest way to find out that a
message was built from a plan that has since changed.

The parser is deliberately forgiving about spacing and strict about structure.
Whitespace in a teletype message is whatever the sending system felt like. The
full stops between fields are not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from holdtrim.errors import DataError
from holdtrim.findings import WATCH, Finding
from holdtrim.sheet.loadsheet import Loadsheet

_FLIGHT = re.compile(r"^([A-Z0-9]{2,3}\d{1,4}[A-Z]?)/(\d{2})\.([A-Z0-9\-]+)\.(\d+)/(\d+)$")
_HOLD = re.compile(r"^(\d)/(\d+)$")

MISMATCH = "message"


@dataclass(frozen=True)
class Offload:
    """One destination line of an LDM."""

    station: str
    total: int
    holds: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadLdm:
    """What one LDM says."""

    flight: str
    day: int
    registration: str
    crew: int
    version: int
    offloads: tuple[Offload, ...] = ()
    supplementary: str = ""

    @property
    def total(self) -> int:
        """Everything the message says is on board."""
        return sum(offload.total for offload in self.offloads)

    def at(self, station: str) -> Offload:
        """One destination line."""
        wanted = station.strip().upper()
        for offload in self.offloads:
            if offload.station == wanted:
                return offload
        raise DataError(f"the message says nothing about {wanted}")


def _flight_line(line: str) -> tuple[str, int, str, int, int]:
    match = _FLIGHT.match(line)
    if match is None:
        raise DataError(f"{line!r} is not the flight line of an LDM")
    flight, day, registration, crew, version = match.groups()
    return flight, int(day), registration, int(crew), int(version)


def _offload_line(line: str) -> Offload:
    parts = line.lstrip("-").split(".")
    if len(parts) < 3:
        raise DataError(f"{line!r} is not a destination line of an LDM")
    station = parts[0].strip().upper()
    total_field = parts[2].strip()
    if not total_field.startswith("T") or not total_field[1:].isdigit():
        raise DataError(f"{line!r} has no total on it")
    holds = {}
    for field_text in parts[3:]:
        match = _HOLD.match(field_text.strip())
        if match is None:
            raise DataError(f"{field_text!r} is not a hold and a weight")
        holds[match.group(1)] = int(match.group(2))
    return Offload(station=station, total=int(total_field[1:]), holds=holds)


def read(text: str) -> ReadLdm:
    """Read an LDM, header and all."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if "LDM" not in lines:
        raise DataError("this is not an LDM, there is no LDM line in it")
    body = lines[lines.index("LDM") + 1 :]
    if not body:
        raise DataError("the LDM has nothing under its type line")
    flight, day, registration, crew, version = _flight_line(body[0])
    offloads = []
    supplementary = ""
    for line in body[1:]:
        if line.startswith("SI"):
            supplementary = line[2:].strip()
            continue
        if line.startswith("-"):
            offloads.append(_offload_line(line))
    return ReadLdm(
        flight=flight,
        day=day,
        registration=registration,
        crew=crew,
        version=version,
        offloads=tuple(offloads),
        supplementary=supplementary,
    )


def compare(message: ReadLdm, sheet: Loadsheet) -> tuple[Finding, ...]:
    """Everything the message and the book disagree about."""
    found = []
    if message.registration != sheet.tail.registration:
        found.append(
            Finding(
                check=MISMATCH,
                where=message.flight,
                detail=(
                    f"the message says {message.registration} and the book says "
                    f"{sheet.tail.registration}"
                ),
            )
        )
    if message.day != sheet.sector.day.day:
        found.append(
            Finding(
                check=MISMATCH,
                where=message.flight,
                detail=f"the message is for day {message.day:02d} and the book is not",
            )
        )
    carried = sheet.by_destination
    for offload in message.offloads:
        expected = carried.get(offload.station, 0)
        if offload.total != expected:
            found.append(
                Finding(
                    check=MISMATCH,
                    where=offload.station,
                    detail=f"the message says {offload.total} kg and the book says {expected} kg",
                    over_by=abs(offload.total - expected),
                )
            )
    for station, weight in carried.items():
        if all(offload.station != station for offload in message.offloads):
            found.append(
                Finding(
                    check=MISMATCH,
                    where=station,
                    detail=f"the book carries {weight} kg for {station} and the message does not",
                    severity=WATCH,
                )
            )
    return tuple(found)
