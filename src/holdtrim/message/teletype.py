"""The envelope every message goes out in.

These messages still travel over a network designed for teleprinters, and the
format has not moved because the systems at the other end have not either. The
rules that matter are simple and unforgiving.

An address is seven characters: three for the station, two for the department,
two for the airline. A message carries a priority and an origin line with the
time it was filed as day, hour and minute. Lines are short, because the
receiving end may still be a printer, and a line that runs long is truncated
rather than wrapped by whoever gets it.

Nothing here is lower case. The network does not carry it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from holdtrim.errors import DataError

LINE_WIDTH = 69
URGENT = "QU"
PRIORITIES = ("QU", "QD", "QK", "QN")

_ADDRESS = re.compile(r"^[A-Z0-9]{7}$")
_FILED = re.compile(r"^\d{6}$")


def address(text: str) -> str:
    """One seven character teletype address."""
    cleaned = text.strip().upper().replace(" ", "")
    if not _ADDRESS.match(cleaned):
        raise DataError(f"{text!r} is not a seven character teletype address")
    return cleaned


def filed_at(day: int, hour: int, minute: int) -> str:
    """The origin line's time stamp, as day of month then hour then minute."""
    if not 1 <= day <= 31:
        raise DataError(f"{day} is not a day of the month")
    if not 0 <= hour <= 23:
        raise DataError(f"{hour} is not an hour")
    if not 0 <= minute <= 59:
        raise DataError(f"{minute} is not a minute")
    return f"{day:02d}{hour:02d}{minute:02d}"


def wrap(text: str, width: int = LINE_WIDTH) -> tuple[str, ...]:
    """Break a long free text line on spaces, never mid word."""
    words = text.split()
    if not words:
        return ()
    lines = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return tuple(lines)


@dataclass(frozen=True)
class Message:
    """One message, ready to go on the wire."""

    kind: str
    addresses: tuple[str, ...]
    origin: str
    filed: str
    body: tuple[str, ...]
    priority: str = URGENT

    def __post_init__(self) -> None:
        kind = self.kind.strip().upper()
        if not kind:
            raise DataError("a message needs a type")
        object.__setattr__(self, "kind", kind)
        if not self.addresses:
            raise DataError(f"the {kind} has nobody to go to")
        object.__setattr__(self, "addresses", tuple(address(one) for one in self.addresses))
        object.__setattr__(self, "origin", address(self.origin))
        if not _FILED.match(self.filed):
            raise DataError(f"{self.filed!r} is not a six digit filing time")
        if self.priority not in PRIORITIES:
            raise DataError(f"{self.priority} is not a teletype priority")
        if not self.body:
            raise DataError(f"the {kind} has no body")

    @property
    def header(self) -> tuple[str, ...]:
        """The priority line and the origin line."""
        return (
            f"{self.priority} {' '.join(self.addresses)}",
            f".{self.origin} {self.filed}",
        )

    def lines(self) -> tuple[str, ...]:
        """Every line of the message, header first."""
        return (*self.header, self.kind, *self.body)

    def render(self) -> str:
        """The message as it goes on the wire."""
        return "\n".join(self.lines()) + "\n"

    @property
    def over_width(self) -> tuple[str, ...]:
        """Any line too long for the network to carry whole."""
        return tuple(line for line in self.lines() if len(line) > LINE_WIDTH)
