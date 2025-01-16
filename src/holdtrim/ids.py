"""The identifiers cargo runs on, and the rules that make them wrong.

None of these are free text. An air waybill number carries its own check
digit, a ULD code says what the ULD is before you look at it, and a station
code is three letters or it is not a station code. Reading them here once
means the rest of the package can hold a parsed value and stop apologising
for the string it came from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from holdtrim.errors import IdentifierError

_AWB = re.compile(r"^(\d{3})-?(\d{7})(\d)$")
_ULD = re.compile(r"^([A-Z]{3})(\d{4,5})([A-Z0-9]{2,3})$")
_FLIGHT = re.compile(r"^([A-Z]{3}|[A-Z][0-9]|[0-9][A-Z]|[A-Z]{2})(\d{1,4})([A-Z]?)$")
_REGISTRATION = re.compile(r"^[A-Z0-9]{1,2}-?[A-Z0-9]{1,5}$")
_STATION = re.compile(r"^[A-Z]{3}$")

CERTIFIED_CONTAINER = "A"
CERTIFIED_PALLET = "P"
NON_CERTIFIED_CONTAINER = "D"
NON_CERTIFIED_PALLET = "F"

ULD_CATEGORIES = {
    CERTIFIED_CONTAINER: "certified container",
    CERTIFIED_PALLET: "certified pallet",
    NON_CERTIFIED_CONTAINER: "non certified container",
    NON_CERTIFIED_PALLET: "non certified pallet",
}


def check_digit(serial: int) -> int:
    """The last digit of an air waybill number is the serial modulo seven."""
    if serial < 0:
        raise IdentifierError(f"air waybill serial cannot be negative: {serial}")
    if serial > 9_999_999:
        raise IdentifierError(f"air waybill serial is longer than seven digits: {serial}")
    return serial % 7


@dataclass(frozen=True, order=True)
class AirWaybill:
    """A master air waybill number, prefix and serial and its check digit."""

    prefix: str
    serial: int

    def __post_init__(self) -> None:
        if not (len(self.prefix) == 3 and self.prefix.isdigit()):
            raise IdentifierError(f"airline prefix is not three digits: {self.prefix!r}")
        check_digit(self.serial)

    @property
    def check(self) -> int:
        """The check digit this number must end in."""
        return check_digit(self.serial)

    def formatted(self) -> str:
        """The way it is written on the document, with the dash."""
        return f"{self.prefix}-{self.serial:07d}{self.check}"

    def plain(self) -> str:
        """Eleven digits with no dash, the way a message carries it."""
        return f"{self.prefix}{self.serial:07d}{self.check}"

    def __str__(self) -> str:
        return self.formatted()


def parse_awb(text: str) -> AirWaybill:
    """Read an air waybill number and check the digit it ends in."""
    cleaned = text.strip().upper().replace(" ", "")
    match = _AWB.match(cleaned)
    if match is None:
        raise IdentifierError(f"not an air waybill number: {text!r}")
    prefix, serial_text, given = match.groups()
    serial = int(serial_text)
    expected = check_digit(serial)
    if int(given) != expected:
        raise IdentifierError(
            f"air waybill {text} fails its check digit, {expected} was expected not {given}"
        )
    return AirWaybill(prefix=prefix, serial=serial)


@dataclass(frozen=True, order=True)
class UldCode:
    """A ULD code: what it is, which one it is, and whose it is."""

    type_code: str
    serial: str
    owner: str

    def __post_init__(self) -> None:
        if self.type_code[0] not in ULD_CATEGORIES:
            raise IdentifierError(f"unknown ULD category letter: {self.type_code[0]!r}")

    @property
    def category(self) -> str:
        """The plain words for the leading letter."""
        return ULD_CATEGORIES[self.type_code[0]]

    @property
    def certified(self) -> bool:
        """Certified ULDs are part of the aircraft and carry a placard."""
        return self.type_code[0] in {CERTIFIED_CONTAINER, CERTIFIED_PALLET}

    @property
    def is_pallet(self) -> bool:
        """A pallet needs a net or an igloo, a container does not."""
        return self.type_code[0] in {CERTIFIED_PALLET, NON_CERTIFIED_PALLET}

    def formatted(self) -> str:
        """The code as it is stencilled on the side."""
        return f"{self.type_code}{self.serial}{self.owner}"

    def __str__(self) -> str:
        return self.formatted()


def parse_uld(text: str) -> UldCode:
    """Read a ULD code, three letters then the serial then the owner."""
    cleaned = text.strip().upper().replace(" ", "")
    match = _ULD.match(cleaned)
    if match is None:
        raise IdentifierError(f"not a ULD code: {text!r}")
    type_code, serial, owner = match.groups()
    return UldCode(type_code=type_code, serial=serial, owner=owner)


@dataclass(frozen=True, order=True)
class Flight:
    """An airline code, a number, and the suffix a duplicate leg carries."""

    carrier: str
    number: int
    suffix: str = ""

    def formatted(self) -> str:
        """Padded to three digits, which is how the schedule prints it."""
        return f"{self.carrier}{self.number:03d}{self.suffix}"

    def __str__(self) -> str:
        return self.formatted()


def parse_flight(text: str) -> Flight:
    """Read a flight designator such as QH412, 5X0100 or the ICAO form AAL412.

    The carrier part is two characters with at least one letter, or three
    letters for the ICAO form. Anything shorter is a number, not a flight.
    """
    cleaned = text.strip().upper().replace(" ", "")
    match = _FLIGHT.match(cleaned)
    if match is None:
        raise IdentifierError(f"not a flight designator: {text!r}")
    carrier, number, suffix = match.groups()
    return Flight(carrier=carrier, number=int(number), suffix=suffix)


def parse_registration(text: str) -> str:
    """Normalise an aircraft registration to upper case with its dash."""
    cleaned = text.strip().upper().replace(" ", "")
    if not _REGISTRATION.match(cleaned):
        raise IdentifierError(f"not an aircraft registration: {text!r}")
    return cleaned


def parse_station(text: str) -> str:
    """Three letters, the IATA station code, upper case."""
    cleaned = text.strip().upper()
    if not _STATION.match(cleaned):
        raise IdentifierError(f"not a three letter station code: {text!r}")
    return cleaned
