from holdtrim.message import cpm
from holdtrim.message.teletype import Message
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.sheet.loadsheet import Loadsheet
from tests.sheet.test_loadsheet import KEY, sheet


def built(made: Loadsheet | None = None) -> Message:
    return cpm.build(
        made if made is not None else sheet(),
        addresses=("LGGKLQH",),
        origin="BLLLDQH",
        filed="121815",
    )


def loaded() -> Loadsheet:
    plan = LoadPlan(
        flight_key=KEY,
        assignments=(
            Assignment(position="11P", weight=2000, uld="PMC12345QH", destination="LGG"),
            Assignment(position="51", weight=300, destination="LGG"),
        ),
    )
    return sheet(plan=plan)


def test_the_flight_line_carries_the_departure_station() -> None:
    assert cpm.flight_line(sheet()) == "QH412/12.OY-JAF.BLL"


def test_a_loaded_position_names_its_device() -> None:
    assert cpm.position_line(loaded(), "11P") == ".11P/PMC12345QH/2000/LGG"


def test_a_position_with_loose_cargo_reads_bulk() -> None:
    assert cpm.position_line(loaded(), "51") == ".51/BULK/300/LGG"


def test_the_positions_that_are_not_used_are_listed() -> None:
    assert cpm.empty_positions(loaded()) == ("21P",)


def test_a_flight_with_nothing_on_it_lists_every_position_as_empty() -> None:
    assert cpm.empty_positions(sheet({})) == ("11P", "21P", "51")


def test_the_body_groups_the_positions_under_their_destination() -> None:
    lines = cpm.body(loaded())
    assert lines[1] == "-LGG"
    assert lines[2].startswith(".11P")


def test_the_empty_positions_come_after_the_loaded_ones() -> None:
    lines = cpm.body(loaded())
    assert lines[-1] == "NIL 21P"


def test_an_empty_flight_still_names_its_destination() -> None:
    assert "-LGG" in cpm.body(sheet({}))


def test_the_message_is_typed_as_a_cpm() -> None:
    assert built(loaded()).kind == "CPM"


def test_the_rendered_message_reads_as_a_cpm() -> None:
    printed = built(loaded()).render()
    assert "CPM\n" in printed
    assert ".11P/PMC12345QH/2000/LGG" in printed


def test_no_line_of_the_message_is_too_long_for_the_wire() -> None:
    assert built(loaded()).over_width == ()


def test_a_flight_with_every_position_used_lists_no_empties() -> None:
    plan = LoadPlan(
        flight_key=KEY,
        assignments=(
            Assignment(position="11P", weight=2000, uld="PMC12345QH", destination="LGG"),
            Assignment(position="21P", weight=900, uld="PMC12346QH", destination="LGG"),
            Assignment(position="51", weight=300, destination="LGG"),
        ),
    )
    assert cpm.empty_positions(sheet(plan=plan)) == ()
    assert not any(line.startswith("NIL") for line in cpm.body(sheet(plan=plan)))
