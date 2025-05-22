"""The class list and the segregation table this operation works to.

The table is the operator's extract of the segregation table in the regulations,
kept here rather than in a spreadsheet because it decides whether a load plan is
legal and a spreadsheet cannot be tested.

Two things are not a simple table lookup and are handled separately.

Class 1 is segregated by compatibility group, not by class. Division 1.4S is the
exception the whole of the rest of class 1 is not, and treating class 1 as one
thing gets that backwards.

Class 7 is segregated by distance rather than by class. The distance comes off
the summed transport index of everything radioactive in the hold, and it grows
as the index does.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from holdtrim.errors import DataError

CLASS_NAMES = {
    "1": "explosives",
    "2.1": "flammable gas",
    "2.2": "non flammable non toxic gas",
    "2.3": "toxic gas",
    "3": "flammable liquid",
    "4.1": "flammable solid",
    "4.2": "spontaneously combustible",
    "4.3": "dangerous when wet",
    "5.1": "oxidiser",
    "5.2": "organic peroxide",
    "6.1": "toxic substance",
    "6.2": "infectious substance",
    "7": "radioactive material",
    "8": "corrosive",
    "9": "miscellaneous dangerous goods",
}

SEGREGATED_PAIRS: tuple[tuple[str, str], ...] = (
    ("2.1", "5.1"),
    ("2.1", "5.2"),
    ("3", "4.3"),
    ("3", "5.1"),
    ("3", "5.2"),
    ("4.1", "5.1"),
    ("4.1", "5.2"),
    ("4.2", "5.1"),
    ("4.2", "5.2"),
    ("4.2", "8"),
    ("4.3", "8"),
    ("5.1", "6.1"),
)


def _both_ways(pairs: tuple[tuple[str, str], ...]) -> dict[str, frozenset[str]]:
    """Read the pairs in both directions, because segregation is mutual.

    The pairs are listed once each so that the list stays readable next to the
    printed table. Keeping the two directions in step by hand is exactly the
    kind of thing that quietly stops being true, so it is done here instead.
    """
    built: dict[str, set[str]] = {}
    for first, second in pairs:
        built.setdefault(first, set()).add(second)
        built.setdefault(second, set()).add(first)
    return {hazard: frozenset(against) for hazard, against in sorted(built.items())}


SEGREGATE: dict[str, frozenset[str]] = _both_ways(SEGREGATED_PAIRS)

RADIOACTIVE_SEPARATION = (
    (Decimal("0.5"), Decimal("0.3")),
    (Decimal("1.0"), Decimal("0.5")),
    (Decimal("2.0"), Decimal("0.7")),
    (Decimal("4.0"), Decimal("1.0")),
    (Decimal("8.0"), Decimal("1.5")),
    (Decimal("12.0"), Decimal("2.0")),
    (Decimal("20.0"), Decimal("2.5")),
    (Decimal("30.0"), Decimal("3.0")),
    (Decimal("40.0"), Decimal("3.5")),
    (Decimal("50.0"), Decimal("4.0")),
)

EXPLOSIVE_EXCEPTION = "1.4S"


def class_name(hazard: str) -> str:
    """The plain words for a class or division."""
    wanted = normalise(hazard)
    if wanted not in CLASS_NAMES:
        raise DataError(f"{hazard} is not a class this table covers")
    return CLASS_NAMES[wanted]


def normalise(hazard: str) -> str:
    """Reduce a division to the key the table is written in.

    Explosives collapse to class 1 because the table treats them as one, and
    everything else keeps its division because the table does not.
    """
    cleaned = hazard.strip().upper()
    if cleaned.startswith("1."):
        return "1"
    return cleaned


def is_explosive_exception(hazard: str) -> bool:
    """Whether this is 1.4S, which travels with almost anything."""
    return hazard.strip().upper() == EXPLOSIVE_EXCEPTION


def must_segregate(first: str, second: str) -> bool:
    """Whether two classes have to be kept apart."""
    left = normalise(first)
    right = normalise(second)
    if left == "1" or right == "1":
        return not (is_explosive_exception(first) and is_explosive_exception(second))
    return right in SEGREGATE.get(left, frozenset())


def conflicts(classes: Iterable[str]) -> tuple[tuple[str, str], ...]:
    """Every pair in a set of classes that may not travel together."""
    listed = sorted({hazard.strip().upper() for hazard in classes})
    found = []
    for i, first in enumerate(listed):
        for second in listed[i + 1 :]:
            if must_segregate(first, second):
                found.append((first, second))
    return tuple(found)


def separation_for(transport_index: Decimal) -> Decimal:
    """Metres a radioactive package has to be kept from the nearest person."""
    if transport_index < 0:
        raise DataError("a transport index cannot be negative")
    if transport_index == 0:
        return Decimal("0.0")
    for ceiling, metres in RADIOACTIVE_SEPARATION:
        if transport_index <= ceiling:
            return metres
    raise DataError(
        f"a transport index of {transport_index} is past the top of the separation table"
    )
