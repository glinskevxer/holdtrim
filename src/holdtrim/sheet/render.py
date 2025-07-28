"""Printing the loadsheet.

The layout is the one that has been faxed, emailed and handed across a desk
for decades, and it is kept because the people reading it can find a figure on
it without looking. The weights run down the left in the order they are worked
out, the distribution sits under them, and the balance figures and the trim are
at the bottom where the crew look first.

Everything is fixed width. A loadsheet gets printed on whatever is in the
office and read on a phone at the aircraft, and a layout that reflows is a
layout where two figures end up on the same line.
"""

from __future__ import annotations

from collections.abc import Sequence

from holdtrim.findings import Finding
from holdtrim.sheet.loadsheet import Loadsheet
from holdtrim.units import format_kilos

WIDTH = 46
RULE = "-" * WIDTH


def _row(label: str, value: str) -> str:
    return f"{label:<28}{value:>18}"


def header(sheet: Loadsheet) -> list[str]:
    """Who, what, where and which edition."""
    flight = sheet.sector
    return [
        "LOADSHEET".center(WIDTH),
        RULE,
        _row("flight", flight.reference),
        _row("date", flight.day.isoformat()),
        _row("aircraft", f"{sheet.tail.registration} {sheet.kind.code}"),
        _row("route", f"{flight.origin} to {flight.destination}"),
        _row("edition", str(sheet.edition)),
        _row("prepared by", sheet.prepared_by),
    ]


def weights(sheet: Loadsheet) -> list[str]:
    """The weight chain, in the order each one is worked out."""
    balance = sheet.balance
    limits = sheet.kind.limits
    return [
        RULE,
        "WEIGHTS".center(WIDTH),
        RULE,
        _row("dry operating weight", format_kilos(sheet.dry_operating_weight)),
        _row("payload", format_kilos(sheet.payload)),
        _row("zero fuel weight", format_kilos(balance.zero_fuel.weight)),
        _row("max zero fuel weight", format_kilos(limits.max_zero_fuel)),
        _row("takeoff fuel", format_kilos(sheet.sector.takeoff_fuel)),
        _row("takeoff weight", format_kilos(balance.takeoff.weight)),
        _row("max takeoff weight", format_kilos(limits.max_takeoff)),
        _row("trip fuel", format_kilos(sheet.sector.trip_fuel)),
        _row("landing weight", format_kilos(balance.landing.weight)),
        _row("max landing weight", format_kilos(limits.max_landing)),
        _row("underload", format_kilos(sheet.underload)),
        _row("limited by", sheet.limiting_weight),
    ]


def distribution(sheet: Loadsheet) -> list[str]:
    """Where the payload is, by position and by compartment."""
    lines = [RULE, "DISTRIBUTION".center(WIDTH), RULE]
    for assignment in sheet.plan.assignments:
        what = assignment.uld if assignment.uld else "bulk"
        lines.append(_row(f"{assignment.position} {what}", format_kilos(assignment.weight)))
    if not sheet.plan.assignments:
        lines.append(_row("nothing loaded", "0"))
    lines.append(RULE)
    for compartment, weight in sheet.by_compartment.items():
        lines.append(_row(f"compartment {compartment}", format_kilos(weight)))
    for where, weight in sheet.by_destination.items():
        lines.append(_row(f"for {where}", format_kilos(weight)))
    return lines


def balance(sheet: Loadsheet) -> list[str]:
    """The three centres of gravity and the setting that follows from them."""
    figures = sheet.balance
    return [
        RULE,
        "BALANCE".center(WIDTH),
        RULE,
        _row("zero fuel index", str(figures.zero_fuel.index)),
        _row("zero fuel percent mac", str(sheet.zero_fuel_percent_mac)),
        _row("takeoff index", str(figures.takeoff.index)),
        _row("takeoff percent mac", str(sheet.takeoff_percent_mac)),
        _row("landing percent mac", str(sheet.landing_percent_mac)),
        _row("stabiliser trim", str(sheet.trim_setting)),
    ]


def problems(found: Sequence[Finding]) -> list[str]:
    """Anything wrong, printed where nobody can miss it."""
    if not found:
        return []
    lines = [RULE, "NOT FOR ISSUE".center(WIDTH), RULE]
    lines.extend(finding.describe() for finding in found)
    return lines


def footer(sheet: Loadsheet) -> list[str]:
    """The last minute change box and the signature block."""
    lines = [RULE, "LAST MINUTE CHANGES".center(WIDTH), RULE]
    lines.extend(sheet.changes.lines())
    if not sheet.changes.empty:
        lines.append(_row("net change", format_kilos(sheet.changes.net)))
        lines.append(_row("handled", format_kilos(sheet.changes.total)))
        if not sheet.changes.within_tolerance:
            lines.append(
                _row("past tolerance by", format_kilos(sheet.changes.over_by)),
            )
    lines.extend(
        [
            RULE,
            "",
            "commander signature ...........................",
            f"issued by {sheet.prepared_by}",
            RULE,
        ]
    )
    return lines


def render(sheet: Loadsheet) -> str:
    """The whole sheet as one block of text."""
    lines = [
        *header(sheet),
        *weights(sheet),
        *distribution(sheet),
        *balance(sheet),
        *problems(sheet.findings),
        *footer(sheet),
    ]
    return "\n".join(lines) + "\n"
