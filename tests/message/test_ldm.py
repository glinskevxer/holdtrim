from holdtrim.message import ldm
from holdtrim.message.teletype import Message
from holdtrim.plan.lmc import Change, Changes
from holdtrim.plan.loadplan import Assignment, LoadPlan
from tests.sheet.test_loadsheet import KEY, sheet


def built() -> Message:
    return ldm.build(
        sheet(),
        addresses=("LGGKLQH",),
        origin="BLLLDQH",
        filed="121815",
    )


def test_the_flight_line_carries_the_registration_and_the_crew() -> None:
    assert ldm.flight_line(sheet()) == "QH412/12.OY-JAF.2/0"


def test_the_version_follows_the_edition() -> None:
    assert ldm.flight_line(sheet().reissued()).endswith("/1")


def test_a_hold_field_is_the_hold_number_and_the_weight() -> None:
    assert ldm.hold_field("MAIN", 2000) == "2/2000"
    assert ldm.hold_field("BULK", 300) == "5/300"


def test_a_compartment_the_message_has_no_number_for_reads_nine() -> None:
    assert ldm.hold_field("NOSE", 100) == "9/100"


def test_the_destination_line_totals_and_splits_by_hold() -> None:
    assert ldm.destination_line(sheet(), "LGG") == "-LGG.0/0/0.T2300.2/2000.5/300"


def test_a_destination_with_nothing_on_board_totals_zero() -> None:
    assert ldm.destination_line(sheet(), "CDG") == "-CDG.0/0/0.T0"


def test_the_body_starts_with_the_flight_line() -> None:
    assert ldm.body(sheet())[0] == "QH412/12.OY-JAF.2/0"


def test_a_device_is_named_in_the_supplementary_line() -> None:
    plan = LoadPlan(
        flight_key=KEY,
        assignments=(Assignment(position="11P", weight=2000, uld="PMC12345QH"),),
    )
    assert ldm.supplementary(sheet(plan=plan)) == ("SI PMC12345QH IN 11P",)


def test_bulk_only_needs_no_supplementary_line() -> None:
    assert ldm.supplementary(sheet()) == ()


def test_a_last_minute_change_reaches_the_supplementary_line() -> None:
    changes = Changes(changes=(Change(position="11P", weight=-200),))
    assert "LMC -200 KG" in ldm.supplementary(sheet(changes=changes))[0]


def test_the_message_is_addressed_and_typed() -> None:
    message = built()
    assert message.kind == "LDM"
    assert message.addresses == ("LGGKLQH",)


def test_the_rendered_message_reads_as_an_ldm() -> None:
    printed = built().render()
    assert "LDM\n" in printed
    assert "-LGG.0/0/0.T2300" in printed


def test_no_line_of_the_message_is_too_long_for_the_wire() -> None:
    assert built().over_width == ()
