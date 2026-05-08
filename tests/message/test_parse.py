import pytest

from holdtrim.errors import DataError
from holdtrim.message import ldm
from holdtrim.message.parse import ReadLdm, compare, read
from holdtrim.plan.loadplan import Assignment, LoadPlan
from tests.sheet.test_loadsheet import KEY, sheet

SENT = "LDM\nQH412/12.OY-JAF.2/0\n-LGG.0/0/0.T2300.2/2000.5/300\nSI PMC12345QH IN 11P\n"


def test_a_message_reads_back_its_flight_line() -> None:
    message = read(SENT)
    assert message.flight == "QH412"
    assert message.day == 12
    assert message.registration == "OY-JAF"
    assert message.crew == 2
    assert message.version == 0


def test_a_message_reads_back_its_destination_line() -> None:
    offload = read(SENT).at("lgg")
    assert offload.total == 2300
    assert offload.holds == {"2": 2000, "5": 300}


def test_the_total_is_every_destination_added_up() -> None:
    assert read(SENT).total == 2300


def test_the_supplementary_line_reads_back() -> None:
    assert read(SENT).supplementary == "PMC12345QH IN 11P"


def test_a_destination_the_message_does_not_carry_is_refused() -> None:
    with pytest.raises(DataError, match="says nothing about CDG"):
        read(SENT).at("CDG")


def test_something_that_is_not_an_ldm_is_refused() -> None:
    with pytest.raises(DataError, match="not an LDM"):
        read("CPM\nQH412/12.OY-JAF.BLL\n")


def test_an_ldm_with_no_body_is_refused() -> None:
    with pytest.raises(DataError, match="nothing under its type line"):
        read("LDM\n")


def test_a_flight_line_of_the_wrong_shape_is_refused() -> None:
    with pytest.raises(DataError, match="not the flight line"):
        read("LDM\nnonsense\n")


def test_a_destination_line_with_no_total_is_refused() -> None:
    with pytest.raises(DataError, match="has no total"):
        read("LDM\nQH412/12.OY-JAF.2/0\n-LGG.0/0/0.2300\n")


def test_a_hold_field_of_the_wrong_shape_is_refused() -> None:
    with pytest.raises(DataError, match="not a hold and a weight"):
        read("LDM\nQH412/12.OY-JAF.2/0\n-LGG.0/0/0.T2300.main/2000\n")


def test_a_destination_line_that_is_too_short_is_refused() -> None:
    with pytest.raises(DataError, match="not a destination line"):
        read("LDM\nQH412/12.OY-JAF.2/0\n-LGG.0/0/0\n")


def test_a_message_built_here_reads_back_the_same() -> None:
    built = ldm.build(sheet(), addresses=("LGGKLQH",), origin="BLLLDQH", filed="121815")
    message = read(built.render())
    assert message.registration == "OY-JAF"
    assert message.at("LGG").total == 2300


def test_a_message_that_agrees_with_the_book_reports_nothing() -> None:
    assert compare(read(SENT), sheet()) == ()


def test_a_different_aeroplane_is_reported() -> None:
    message = read(SENT.replace("OY-JAF", "OY-JAG"))
    assert "the message says OY-JAG" in compare(message, sheet())[0].detail


def test_a_different_day_is_reported() -> None:
    message = read(SENT.replace("QH412/12", "QH412/14"))
    assert any("day 14" in finding.detail for finding in compare(message, sheet()))


def test_a_different_weight_is_reported() -> None:
    message = read(SENT.replace("T2300", "T2400"))
    found = compare(message, sheet())
    assert found[0].over_by == 100


def test_a_destination_the_message_leaves_out_is_a_note() -> None:
    plan = LoadPlan(
        flight_key=KEY,
        assignments=(
            Assignment(position="11P", weight=2000, destination="LGG"),
            Assignment(position="51", weight=300, destination="CDG"),
        ),
    )
    found = compare(read(SENT.replace("T2300", "T2000")), sheet(plan=plan))
    assert any(finding.severity == "watch" for finding in found)


def test_a_message_can_be_built_by_hand() -> None:
    message = ReadLdm(flight="QH412", day=12, registration="OY-JAF", crew=2, version=0)
    assert message.total == 0
