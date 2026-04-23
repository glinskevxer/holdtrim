import pytest

from holdtrim.errors import DataError
from holdtrim.message import mvt
from holdtrim.message.mvt import Arrival, Departure, clock, delay
from tests.sheet.test_loadsheet import sector


def departure(**changes: object) -> Departure:
    fields: dict[str, object] = {
        "off_blocks": "1815",
        "airborne": "1830",
        "estimated_arrival": "1930",
        "arrival_station": "LGG",
    }
    fields.update(changes)
    return Departure(**fields)  # type: ignore[arg-type]


def test_a_time_is_four_digits() -> None:
    assert clock(" 1815 ") == "1815"


def test_something_that_is_not_a_time_is_refused() -> None:
    with pytest.raises(DataError, match="not a time written as HHMM"):
        clock("2515")


def test_a_delay_code_is_two_characters() -> None:
    assert delay("41", 25) == ("41", 25)
    assert delay("ab", 25) == ("AB", 25)


def test_a_delay_code_of_the_wrong_shape_is_refused() -> None:
    with pytest.raises(DataError, match="two character delay code"):
        delay("4123", 25)


def test_a_delay_of_no_minutes_is_refused() -> None:
    with pytest.raises(DataError, match="is not a delay"):
        delay("41", 0)


def test_the_departure_line_carries_both_times_and_the_arrival() -> None:
    assert departure().lines() == ("AD1815/1830 EA1930 LGG",)


def test_a_delay_adds_a_second_line() -> None:
    reported = departure(delays=(("41", 25),))
    assert reported.lines()[1] == "DL41/0025"
    assert reported.delayed_by == 25


def test_two_delays_go_on_one_line() -> None:
    reported = departure(delays=(("41", 25), ("93", 10)))
    assert reported.lines()[1] == "DL41/0025 DL93/0010"
    assert reported.delayed_by == 35


def test_the_arrival_line_carries_touchdown_and_on_blocks() -> None:
    assert Arrival(touchdown="1928", on_blocks="1935").lines() == ("AA1928/1935",)


def test_the_body_names_the_flight_and_the_station() -> None:
    lines = mvt.body(sector(), departure(), station="bll")
    assert lines[0] == "QH412/12.OY-JAF.BLL"
    assert lines[1].startswith("AD")


def test_the_message_is_typed_as_a_mvt() -> None:
    message = mvt.build(
        sector(),
        departure(),
        station="BLL",
        addresses=("LGGKLQH",),
        origin="BLLLDQH",
        filed="121815",
    )
    assert message.kind == "MVT"
    assert "AD1815/1830 EA1930 LGG" in message.render()


def test_an_arrival_message_carries_the_arrival_line() -> None:
    message = mvt.build(
        sector(),
        Arrival(touchdown="1928", on_blocks="1935"),
        station="LGG",
        addresses=("BLLKLQH",),
        origin="LGGLDQH",
        filed="121940",
    )
    assert "AA1928/1935" in message.render()
