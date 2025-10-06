from decimal import Decimal

import pytest

from holdtrim.errors import DataError, RuleError
from holdtrim.model.fuel import FuelPoint, FuelTable


def table() -> FuelTable:
    return FuelTable(
        points=(
            FuelPoint(weight=0, index=Decimal("0.0")),
            FuelPoint(weight=1000, index=Decimal("-2.4")),
            FuelPoint(weight=2000, index=Decimal("-3.6")),
            FuelPoint(weight=3000, index=Decimal("-2.8")),
            FuelPoint(weight=4500, index=Decimal("1.2")),
        )
    )


def test_a_table_with_one_row_is_refused() -> None:
    with pytest.raises(DataError, match="at least two rows"):
        FuelTable(points=(FuelPoint(weight=0, index=Decimal("0")),))


def test_rows_out_of_order_are_refused() -> None:
    with pytest.raises(DataError, match="not in weight order"):
        FuelTable(points=tuple(reversed(table().points)))


def test_a_table_that_does_not_start_at_zero_is_refused() -> None:
    with pytest.raises(DataError, match="start at zero fuel"):
        FuelTable(
            points=(
                FuelPoint(weight=500, index=Decimal("-1.2")),
                FuelPoint(weight=1000, index=Decimal("-2.4")),
            )
        )


def test_no_fuel_moves_the_index_by_nothing() -> None:
    assert table().index_at(0) == Decimal("0.0")


def test_a_printed_row_reads_straight_off() -> None:
    assert table().index_at(2000) == Decimal("-3.6")


def test_a_quantity_between_rows_interpolates() -> None:
    assert table().index_at(1500) == Decimal("-3.0")
    assert table().index_at(3750) == Decimal("-0.8")


def test_the_curve_turns_back_on_itself() -> None:
    assert table().index_at(2000) < table().index_at(1000)
    assert table().index_at(3000) > table().index_at(2000)


def test_the_capacity_is_the_last_printed_row() -> None:
    assert table().capacity == 4500


def test_more_fuel_than_the_table_covers_is_refused() -> None:
    with pytest.raises(RuleError, match="runs 0 to 4500 kg"):
        table().index_at(5000)


def test_a_negative_quantity_is_not_covered() -> None:
    assert not table().covers(-1)


def test_burning_fuel_moves_the_index_by_the_difference() -> None:
    assert table().burn_between(4500, 3000) == Decimal("-4.0")


def test_burning_nothing_moves_nothing() -> None:
    assert table().burn_between(2000, 2000) == Decimal("0.0")


def test_the_rows_come_back_for_a_report() -> None:
    assert table().rows()[1] == (1000, Decimal("-2.4"))
    assert len(table().rows()) == 5
