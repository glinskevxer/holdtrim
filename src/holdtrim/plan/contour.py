"""Which positions a shaped device fits.

The fuselage is not a box. It tapers at both ends of every compartment, and a
device with a flat top will not go under the roof where it does. A device built
to the sloping contour will, and it wastes space anywhere else.

The weight schedule this operation flies to does not publish a contour per
position, so the office works to a rule of thumb that has been right for
fifteen years: the first and last position of each compartment are where it
tapers. It is written down here rather than carried in somebody's head, and it
is a rule of thumb rather than a certified limit, which is why breaking it is a
note and not a refusal.
"""

from __future__ import annotations

from holdtrim.findings import WATCH, Finding
from holdtrim.model.hold import HoldLayout
from holdtrim.model.position import COMPARTMENTS
from holdtrim.model.uld import FLAT, SLOPING

CONTOUR = "contour"
LEAST_POSITIONS_TO_TAPER = 3


def tapered(layout: HoldLayout) -> frozenset[str]:
    """The positions where the fuselage narrows, by the office's rule."""
    ends: set[str] = set()
    for compartment in COMPARTMENTS:
        held = [position for position in layout.by_arm() if position.compartment == compartment]
        if len(held) < LEAST_POSITIONS_TO_TAPER:
            continue
        ends.add(held[0].code)
        ends.add(held[-1].code)
    return frozenset(ends)


def fits(layout: HoldLayout, position: str, contour: str) -> bool:
    """Whether a device of that contour belongs in that position."""
    wanted = position.strip().upper()
    shape = contour.strip().lower()
    if shape == SLOPING:
        return True
    return wanted not in tapered(layout)


def wasted(layout: HoldLayout, position: str, contour: str) -> bool:
    """Whether a sloping device is being used where a flat one would do."""
    return contour.strip().lower() == SLOPING and position.strip().upper() not in tapered(layout)


def check(layout: HoldLayout, loaded: dict[str, str]) -> tuple[Finding, ...]:
    """Every position whose device is the wrong shape for it."""
    found = []
    for position, contour in sorted(loaded.items()):
        if not fits(layout, position, contour):
            found.append(
                Finding(
                    check=CONTOUR,
                    where=position,
                    detail=(
                        f"a {FLAT} device is planned where the fuselage tapers, "
                        "check it goes under the roof"
                    ),
                    severity=WATCH,
                )
            )
        elif wasted(layout, position, contour):
            found.append(
                Finding(
                    check=CONTOUR,
                    where=position,
                    detail=f"a {SLOPING} device is in a square position and wastes the space",
                    severity=WATCH,
                )
            )
    return tuple(found)
