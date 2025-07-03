"""Everything that can be wrong with a set of figures, gathered in one place.

The checks are deliberately all run rather than stopping at the first refusal.
A load controller fixing one problem wants to know about the other three now,
not after another round trip to the ramp, and a plan that is over on weight is
very often also outside the envelope for a related reason.

Each finding names what was checked, where, and by how much it failed. The
"by how much" is what makes a finding actionable: 40 kg over a position limit
is one carton moved, and 900 kg over the zero fuel weight is an offload.
"""

from __future__ import annotations

from decimal import Decimal

from holdtrim.balance.loading import Balance
from holdtrim.findings import Finding
from holdtrim.model.envelope import LANDING, TAKEOFF, ZERO_FUEL

STRUCTURAL = "structural"
ENVELOPE = "envelope"
POSITION = "position"
RUNNING_LOAD = "running load"
AREA_LOAD = "area load"
COMBINED = "combined limit"

ENVELOPE_FOR_CONDITION = {
    ZERO_FUEL: ZERO_FUEL,
    TAKEOFF: TAKEOFF,
    LANDING: LANDING,
}


def structural(balance: Balance) -> tuple[Finding, ...]:
    """The four certificate weights, checked against what is planned."""
    limits = balance.kind.limits
    checked = (
        (ZERO_FUEL, balance.zero_fuel.weight, limits.max_zero_fuel),
        (TAKEOFF, balance.takeoff.weight, limits.max_takeoff),
        (LANDING, balance.landing.weight, limits.max_landing),
        ("ramp", balance.ramp_weight, limits.max_ramp),
    )
    found = []
    for name, actual, allowed in checked:
        if actual > allowed:
            found.append(
                Finding(
                    check=STRUCTURAL,
                    where=name,
                    detail=f"{actual} kg against a limit of {allowed} kg",
                    over_by=actual - allowed,
                )
            )
    return tuple(found)


def envelope(balance: Balance) -> tuple[Finding, ...]:
    """Each of the three conditions read against its own certified shape."""
    found = []
    for condition in balance.conditions:
        shape = balance.kind.envelope(ENVELOPE_FOR_CONDITION[condition.name])
        if not shape.covers(condition.weight):
            found.append(
                Finding(
                    check=ENVELOPE,
                    where=condition.name,
                    detail=(
                        f"{condition.weight} kg is off the {shape.name} envelope, "
                        f"which runs {shape.lightest} to {shape.heaviest} kg"
                    ),
                )
            )
            continue
        if not shape.contains(condition.weight, condition.index):
            forward, aft = shape.limits_at(condition.weight)
            found.append(
                Finding(
                    check=ENVELOPE,
                    where=condition.name,
                    detail=(
                        f"index {condition.index} is outside {forward} to {aft} "
                        f"at {condition.weight} kg"
                    ),
                )
            )
    return tuple(found)


def positions(balance: Balance) -> tuple[Finding, ...]:
    """Position weight, running load and area load, position by position."""
    found = []
    for code, weight in sorted(balance.loaded_positions.items()):
        position = balance.kind.layout.position(code)
        over = position.over_weight_by(weight)
        if over:
            found.append(
                Finding(
                    check=POSITION,
                    where=code,
                    detail=f"{weight} kg against a limit of {position.max_weight} kg",
                    over_by=over,
                )
            )
        running = position.running_load(weight)
        if running > position.max_running_load:
            found.append(
                Finding(
                    check=RUNNING_LOAD,
                    where=code,
                    detail=f"{running} kg/m against a limit of {position.max_running_load} kg/m",
                    over_by=running - position.max_running_load,
                )
            )
        area = position.area_load(weight)
        if area > position.max_area_load:
            found.append(
                Finding(
                    check=AREA_LOAD,
                    where=code,
                    detail=f"{area} kg/sqm against a limit of {position.max_area_load} kg/sqm",
                    over_by=area - position.max_area_load,
                )
            )
    return tuple(found)


def combined(balance: Balance) -> tuple[Finding, ...]:
    """The limits that span more than one position."""
    carried = balance.loaded_positions
    found = []
    for limit in balance.kind.layout.cumulative:
        over = limit.over_by(carried)
        if over:
            total = sum(carried.get(code, 0) for code in limit.positions)
            found.append(
                Finding(
                    check=COMBINED,
                    where="+".join(limit.positions),
                    detail=f"{total} kg against a limit of {limit.max_weight} kg",
                    over_by=over,
                )
            )
    return tuple(found)


def check(balance: Balance) -> tuple[Finding, ...]:
    """Every check, all of them run, in the order a controller reads them."""
    return (*structural(balance), *envelope(balance), *positions(balance), *combined(balance))


def legal(balance: Balance) -> bool:
    """Whether the plan may be flown as it stands."""
    return not check(balance)


def worst_margin(balance: Balance) -> Decimal:
    """The tightest envelope margin across the three conditions."""
    margins = []
    for condition in balance.conditions:
        shape = balance.kind.envelope(ENVELOPE_FOR_CONDITION[condition.name])
        if shape.covers(condition.weight):
            margins.append(shape.margin(condition.weight, condition.index))
    if not margins:
        return Decimal("0.0")
    return min(margins)
