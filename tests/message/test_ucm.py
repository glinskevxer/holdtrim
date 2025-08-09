import pytest

from holdtrim.errors import DataError
from holdtrim.message import ucm
from holdtrim.message.ucm import DeviceMovement
from holdtrim.model.uld import uld
from tests.sheet.test_loadsheet import sector


def movements() -> tuple[DeviceMovement, ...]:
    return (
        DeviceMovement(uld="AKE10001QH", direction="on", state="E"),
        DeviceMovement(uld="PMC12345QH", direction="off", state="L"),
    )


def test_a_movement_normalises_its_code_and_direction() -> None:
    movement = DeviceMovement(uld="pmc12345qh", direction="off", state="l")
    assert movement.uld == "PMC12345QH"
    assert movement.direction == "OFF"
    assert movement.state == "L"


def test_a_direction_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="not a direction"):
        DeviceMovement(uld="PMC12345QH", direction="sideways")


def test_a_state_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="not a state"):
        DeviceMovement(uld="PMC12345QH", direction="on", state="X")


def test_a_damaged_device_says_so() -> None:
    assert DeviceMovement(uld="PMC12345QH", direction="off", state="D").damaged
    assert not DeviceMovement(uld="PMC12345QH", direction="off", state="E").damaged


def test_a_movement_reads_as_one_line() -> None:
    assert movements()[1].line() == "OFF.PMC12345QH/L"


def test_the_state_letter_comes_off_the_device() -> None:
    device = uld(code="PMC12345QH", tare=110, max_gross=4626, at_station="BLL")
    assert ucm.state_of(device, loaded=True) == "L"
    assert ucm.state_of(device, loaded=False) == "E"


def test_damage_beats_whatever_is_in_it() -> None:
    broken = uld(code="PMC12345QH", tare=110, max_gross=4626, at_station="BLL", condition="damaged")
    assert ucm.state_of(broken, loaded=True) == "D"


def test_the_body_names_the_flight_and_the_station() -> None:
    lines = ucm.body(sector(), movements(), station="bll")
    assert lines[0] == "QH412/12.OY-JAF.BLL"
    assert lines[1] == "-LGG"


def test_everything_going_on_is_listed_before_what_comes_off() -> None:
    lines = ucm.body(sector(), movements(), station="BLL")
    assert lines[2].startswith("ON.")
    assert lines[3].startswith("OFF.")


def test_the_message_is_typed_as_a_ucm() -> None:
    message = ucm.build(
        sector(),
        movements(),
        station="BLL",
        addresses=("LGGKLQH",),
        origin="BLLLDQH",
        filed="121815",
    )
    assert message.kind == "UCM"
    assert "OFF.PMC12345QH/L" in message.render()


def test_a_message_with_nothing_to_report_is_refused() -> None:
    with pytest.raises(DataError, match="nothing to report"):
        ucm.build(
            sector(),
            (),
            station="BLL",
            addresses=("LGGKLQH",),
            origin="BLLLDQH",
            filed="121815",
        )
