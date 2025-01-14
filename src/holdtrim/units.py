"""Quantities, and the rounding the trade actually uses.

Three quantities run through everything here.

* Weight is whole kilograms. Nothing downstream carries a fraction of a kilo,
  a loadsheet has never printed one, and a teletype message cannot express one.
* Balance arms and lengths are metres to three places, because that is the
  precision a weight schedule is published in.
* Index is a signed decimal to one place. It is not a weight and it is not a
  distance, it is the scaled moment the trade computes balance with.

Rounding is half up, away from zero, in every case. Python's default is
half-even, which is the right default for statistics and the wrong one here:
a weight schedule that says 12.5 rounds to 13 means 13 on every row.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from holdtrim.errors import UnitError

KILO = Decimal(1)
METRE_PLACES = Decimal("0.001")
INDEX_PLACES = Decimal("0.1")
PERCENT_PLACES = Decimal("0.1")

Number = int | str | Decimal


def _decimal(value: Number, what: str) -> Decimal:
    """Read anything the callers accept as a Decimal, or say why not."""
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, bool):
        raise UnitError(f"{what} cannot be a true or false value")
    elif isinstance(value, int):
        parsed = Decimal(value)
    else:
        text = value.strip().replace(" ", "")
        if not text:
            raise UnitError(f"{what} is blank")
        try:
            parsed = Decimal(text)
        except InvalidOperation:
            raise UnitError(f"{what} is not a number: {value!r}") from None
    if not parsed.is_finite():
        raise UnitError(f"{what} is not a finite number: {value!r}")
    return parsed


def round_half_up(value: Decimal, places: Decimal) -> Decimal:
    """Quantize away from zero at the halfway point, the way a schedule reads."""
    return value.quantize(places, rounding="ROUND_HALF_UP")


def to_kilos(value: Number, *, what: str = "weight") -> int:
    """Whole kilograms, never negative."""
    parsed = _decimal(value, what)
    if parsed < 0:
        raise UnitError(f"{what} cannot be negative: {value!r}")
    return int(round_half_up(parsed, KILO))


def to_metres(value: Number, *, what: str = "arm") -> Decimal:
    """Metres to three places. Arms forward of the datum are negative."""
    return round_half_up(_decimal(value, what), METRE_PLACES)


def to_index(value: Number, *, what: str = "index") -> Decimal:
    """Index units to one place, signed."""
    return round_half_up(_decimal(value, what), INDEX_PLACES)


def to_percent(value: Number, *, what: str = "percentage") -> Decimal:
    """A percentage to one place, signed, because trim can read negative."""
    return round_half_up(_decimal(value, what), PERCENT_PLACES)


def parse_weight(text: str, *, what: str = "weight") -> int:
    """Read a weight written the way a handling agent writes one.

    ``1200``, ``1200kg``, ``1200 KG`` and ``1.2t`` all mean the same thing.
    """
    stripped = text.strip().lower().replace(" ", "")
    if stripped.endswith("kg"):
        return to_kilos(stripped[:-2], what=what)
    if stripped.endswith("t"):
        tonnes = _decimal(stripped[:-1], what)
        return to_kilos(tonnes * 1000, what=what)
    return to_kilos(stripped, what=what)


def format_kilos(kilos: int) -> str:
    """Group a weight for a printed report. Messages do not use this."""
    return f"{kilos:,}".replace(",", " ")


def sum_kilos(weights: Iterable[int]) -> int:
    """Add weights that are already whole kilograms."""
    total = 0
    for weight in weights:
        if weight < 0:
            raise UnitError(f"weight cannot be negative: {weight!r}")
        total += weight
    return total
