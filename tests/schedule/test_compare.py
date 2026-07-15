from dataclasses import replace
from decimal import Decimal

from holdtrim.model.aircraft import StructuralLimits
from holdtrim.model.envelope import Envelope, EnvelopePoint
from holdtrim.model.fuel import FuelPoint, FuelTable
from holdtrim.model.hold import HoldLayout
from holdtrim.schedule.compare import Change, differences, same
from tests.fleet.test_type_store import a_type, position


def test_a_schedule_compared_with_itself_says_nothing() -> None:
    assert differences(a_type(), a_type()) == ()
    assert same(a_type(), a_type())


def test_a_change_describes_itself() -> None:
    change = Change(about="geometry", field="lemac", was="11.409", now="11.500")
    assert change.describe() == "geometry lemac: 11.409 became 11.500"


def test_a_changed_structural_limit_is_found() -> None:
    heavier = replace(
        a_type(),
        limits=StructuralLimits(
            max_ramp=23050, max_takeoff=22800, max_landing=22350, max_zero_fuel=21000
        ),
    )
    found = differences(a_type(), heavier)
    assert found[0].field == "max_zero_fuel"
    assert found[0].now == "21000"


def test_a_changed_geometry_is_found() -> None:
    moved = replace(a_type(), geometry=replace(a_type().geometry, lemac=Decimal("11.500")))
    found = differences(a_type(), moved)
    assert found[0].about == "geometry"


def test_a_changed_position_limit_is_found() -> None:
    changed = replace(
        a_type(),
        layout=HoldLayout(
            positions=(
                replace(a_type().layout.position("11P"), max_weight=3000),
                a_type().layout.position("21P"),
                a_type().layout.position("51"),
            ),
            cumulative=a_type().layout.cumulative,
        ),
    )
    found = differences(a_type(), changed)
    assert found[0].field == "11P max_weight"


def test_a_position_that_has_gone_is_found() -> None:
    smaller = replace(
        a_type(),
        layout=HoldLayout(positions=(a_type().layout.position("11P"),)),
    )
    found = differences(a_type(), smaller)
    assert any(change.now == "gone" for change in found)


def test_a_position_that_is_new_is_found() -> None:
    bigger = replace(
        a_type(),
        layout=HoldLayout(
            positions=(*a_type().layout.positions, position("31P", "15.800")),
            cumulative=a_type().layout.cumulative,
        ),
    )
    found = differences(a_type(), bigger)
    assert any(change.now == "added" for change in found)


def test_a_changed_envelope_is_found() -> None:
    shape = (
        EnvelopePoint(weight=13000, forward_index=Decimal("31"), aft_index=Decimal("66")),
        EnvelopePoint(weight=20800, forward_index=Decimal("38"), aft_index=Decimal("58")),
    )
    changed = replace(
        a_type(),
        envelopes=(
            Envelope(name="zero fuel", points=shape),
            a_type().envelope("takeoff"),
            a_type().envelope("landing"),
        ),
    )
    found = differences(a_type(), changed)
    assert any(change.about == "envelope" for change in found)


def test_a_changed_fuel_table_is_found() -> None:
    changed = replace(
        a_type(),
        fuel=FuelTable(
            points=(
                FuelPoint(weight=0, index=Decimal("0.0")),
                FuelPoint(weight=4500, index=Decimal("2.0")),
            )
        ),
    )
    found = differences(a_type(), changed)
    assert found[0].field == "fuel index"


def test_a_changed_trim_table_is_found() -> None:
    changed = replace(a_type(), trim=replace(a_type().trim, points=a_type().trim.points[:2]))
    found = differences(a_type(), changed)
    assert any(change.field == "trim" for change in found)
