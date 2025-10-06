from decimal import Decimal

import pytest

from holdtrim.errors import DataError, RuleError
from holdtrim.model.trim import TrimPoint, TrimTable


def table() -> TrimTable:
    return TrimTable(
        points=(
            TrimPoint(percent_mac=Decimal("15.0"), setting=Decimal("5.5")),
            TrimPoint(percent_mac=Decimal("25.0"), setting=Decimal("3.5")),
            TrimPoint(percent_mac=Decimal("35.0"), setting=Decimal("1.5")),
        )
    )


def test_a_table_with_one_row_is_refused() -> None:
    with pytest.raises(DataError, match="at least two rows"):
        TrimTable(points=(TrimPoint(percent_mac=Decimal("15"), setting=Decimal("5.5")),))


def test_rows_out_of_order_are_refused() -> None:
    with pytest.raises(DataError, match="not in order of percent chord"):
        TrimTable(points=tuple(reversed(table().points)))


def test_the_ends_of_the_table_read_back() -> None:
    assert table().forward_end == Decimal("15.0")
    assert table().aft_end == Decimal("35.0")


def test_a_printed_row_reads_straight_off() -> None:
    assert table().setting_at(Decimal("25.0")) == Decimal("3.5")


def test_a_reading_between_rows_interpolates() -> None:
    assert table().setting_at(Decimal("20.0")) == Decimal("4.5")
    assert table().setting_at(Decimal("30.0")) == Decimal("2.5")


def test_the_setting_falls_as_the_centre_of_gravity_moves_aft() -> None:
    assert table().setting_at(Decimal("16.0")) > table().setting_at(Decimal("34.0"))


def test_a_reading_forward_of_the_table_is_refused() -> None:
    with pytest.raises(RuleError, match="runs 15.0 to 35.0"):
        table().setting_at(Decimal("14.9"))


def test_a_reading_aft_of_the_table_is_refused() -> None:
    with pytest.raises(RuleError, match="off the trim table"):
        table().setting_at(Decimal("35.1"))


def test_the_table_says_whether_it_covers_a_reading() -> None:
    assert table().covers(Decimal("25.0"))
    assert not table().covers(Decimal("40.0"))


def test_the_rows_come_back_for_a_report() -> None:
    assert table().rows()[0] == (Decimal("15.0"), Decimal("5.5"))
    assert len(table().rows()) == 3
