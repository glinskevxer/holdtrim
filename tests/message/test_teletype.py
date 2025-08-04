import pytest

from holdtrim.errors import DataError
from holdtrim.message.teletype import Message, address, filed_at, wrap


def message(**changes: object) -> Message:
    fields: dict[str, object] = {
        "kind": "LDM",
        "addresses": ("LGGKLQH", "BLLKLQH"),
        "origin": "BLLLDQH",
        "filed": "121815",
        "body": ("QH412/12.OY-JAF.7/0",),
    }
    fields.update(changes)
    return Message(**fields)  # type: ignore[arg-type]


def test_an_address_is_seven_characters() -> None:
    assert address("bllkdqh") == "BLLKDQH"


def test_something_that_is_not_an_address_is_refused() -> None:
    with pytest.raises(DataError, match="seven character teletype address"):
        address("BLL")


def test_the_filing_time_is_day_hour_minute() -> None:
    assert filed_at(12, 18, 15) == "121815"
    assert filed_at(1, 0, 0) == "010000"


def test_a_day_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="not a day of the month"):
        filed_at(32, 18, 15)


def test_an_hour_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="not an hour"):
        filed_at(12, 24, 15)


def test_a_minute_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="not a minute"):
        filed_at(12, 18, 60)


def test_a_short_line_does_not_wrap() -> None:
    assert wrap("LOADED IN 11P") == ("LOADED IN 11P",)


def test_a_long_line_breaks_on_spaces() -> None:
    text = " ".join(["WORD"] * 30)
    lines = wrap(text, width=20)
    assert all(len(line) <= 20 for line in lines)
    assert " ".join(lines) == text


def test_nothing_wraps_to_nothing() -> None:
    assert wrap("   ") == ()


def test_a_message_carries_a_priority_and_an_origin_line() -> None:
    assert message().header == ("QU LGGKLQH BLLKLQH", ".BLLLDQH 121815")


def test_the_type_goes_on_its_own_line() -> None:
    assert message().lines()[2] == "LDM"


def test_a_message_with_no_type_is_refused() -> None:
    with pytest.raises(DataError, match="needs a type"):
        message(kind="  ")


def test_a_message_with_nobody_to_go_to_is_refused() -> None:
    with pytest.raises(DataError, match="nobody to go to"):
        message(addresses=())


def test_a_message_with_no_body_is_refused() -> None:
    with pytest.raises(DataError, match="has no body"):
        message(body=())


def test_a_bad_filing_time_is_refused() -> None:
    with pytest.raises(DataError, match="six digit filing time"):
        message(filed="1815")


def test_a_priority_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="not a teletype priority"):
        message(priority="ZZ")


def test_the_rendered_message_ends_with_a_newline() -> None:
    printed = message().render()
    assert printed.endswith("QH412/12.OY-JAF.7/0\n")


def test_a_message_that_fits_reports_no_long_lines() -> None:
    assert message().over_width == ()


def test_a_long_line_is_reported() -> None:
    assert message(body=("X" * 80,)).over_width == ("X" * 80,)
