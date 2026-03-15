"""The glossary, and the check that it still describes this codebase.

Load control has a vocabulary and most of it is not guessable. Somebody reading
this package for the first time meets index, arm, MAC, underload and dry
operating weight in the first ten minutes, and none of those mean what they
sound like.

The glossary is written by hand because definitions have to be. What is
generated is the document, and what is checked is that every term still appears
somewhere in the source. A glossary that describes a version of the code that
no longer exists is worse than none.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from holdtrim.tools.sources import ROOT, package_files

DOCUMENT = ROOT / "docs" / "glossary.md"

TERMS: dict[str, str] = {
    "arm": (
        "The distance from the datum to a position, in metres. Arms forward of "
        "the datum are negative."
    ),
    "index": (
        "A scaled moment. Weight times distance from the reference arm, divided "
        "by a constant the schedule chooses, added to a constant it also chooses."
    ),
    "mac": (
        "Mean aerodynamic chord. The centre of gravity is quoted as a percentage "
        "along it, and that percentage is what the crew set the trim from."
    ),
    "lemac": "The arm of the leading edge of the mean aerodynamic chord.",
    "dry operating weight": (
        "The aeroplane ready to work with no payload and no usable fuel: airframe, "
        "crew, their bags, and the equipment that lives on board."
    ),
    "zero fuel weight": (
        "Dry operating weight plus payload. The weight the wing carries as bending "
        "load, and the only one of the three a load controller can change."
    ),
    "underload": (
        "How much more payload the limits would have allowed. There are three "
        "limits and which one binds changes with the fuel."
    ),
    "uld": (
        "Unit load device. The container or pallet the cargo flies in. A certified "
        "one is part of the aeroplane and its tare weight is on the loadsheet."
    ),
    "tare": "What a device weighs empty. Dead weight the aeroplane lifts and nobody pays for.",
    "running load": (
        "Weight per metre of fuselage under a position. A floor rating, checked "
        "separately from the position's weight limit."
    ),
    "cumulative limit": (
        "A weight limit shared by a run of positions, always less than the sum of "
        "them. The limit that gets missed, because each position looks legal."
    ),
    "loadsheet": (
        "The document the commander signs. Every figure on it is derived and none is typed in."
    ),
    "lmc": (
        "Last minute change. A change after the loadsheet is issued, written in a "
        "box and initialled, up to a weight the operator sets."
    ),
    "ldm": "Load distribution message. What is on board and roughly where.",
    "cpm": "Container pallet message. Exactly which device is in which position.",
    "ucm": "ULD control message. Which devices went on and came off.",
    "notoc": (
        "Notification to captain. What dangerous goods are on board and where, so "
        "that a fire in a hold is a known quantity."
    ),
    "segregation": (
        "Two classes of dangerous goods that may not share a position, and may not "
        "be in neighbouring positions when they are loose."
    ),
    "transport index": (
        "How radioactive a package is, for loading purposes. The indices add up "
        "across the aeroplane and decide how far things have to be kept apart."
    ),
    "demurrage": "What a station owes for holding a device past its free days.",
}


def render() -> str:
    """The glossary as a document."""
    lines = [
        "# holdtrim glossary",
        "",
        "The words this package uses, in the sense the trade uses them.",
        "Run `python -m holdtrim.tools.build_glossary` to write this file again.",
        "",
    ]
    for term, meaning in sorted(TERMS.items()):
        lines.append(f"**{term}**")
        lines.append("")
        lines.append(meaning)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def missing_from_source() -> list[str]:
    """Every term the source no longer mentions anywhere."""
    text = " ".join(path.read_text(encoding="utf-8").lower() for path in package_files())
    return [
        term for term in sorted(TERMS) if term.replace(" ", "_") not in text and term not in text
    ]


def main(argv: list[str] | None = None) -> int:
    """Write the glossary, or check it against the source."""
    parser = argparse.ArgumentParser(description="Build the glossary.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path, default=DOCUMENT)
    arguments = parser.parse_args(argv)
    stale = missing_from_source()
    for term in stale:
        print(f"the glossary defines {term!r} and the source never mentions it")
    wanted = render()
    if arguments.check:
        if not arguments.out.exists():
            print(f"{arguments.out} has never been written")
            return 1
        if arguments.out.read_text(encoding="utf-8") != wanted:
            print(f"{arguments.out} is out of date, run python -m holdtrim.tools.build_glossary")
            return 1
        print(f"{arguments.out} is current, {len(TERMS)} terms")
        return 1 if stale else 0
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(wanted, encoding="utf-8")
    print(f"wrote {arguments.out}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
