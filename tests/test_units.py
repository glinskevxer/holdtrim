from decimal import Decimal

import pytest

from holdtrim.errors import UnitError
from holdtrim.units import (
    INDEX_PLACES,
    KILO,
    format_kilos,
    parse_weight,
    round_half_up,
    sum_kilos,
    to_index,
    to_kilos,
    to_metres,
    to_percent,
)


def test_half_a_kilo_rounds_up_not_to_even() -> None:
    assert to_kilos("12.5") == 13
    assert to_kilos("13.5") == 14


def test_a_weight_below_half_rounds_down() -> None:
    assert to_kilos("12.49") == 12


def test_whole_kilos_pass_through_untouched() -> None:
    assert to_kilos(2450) == 2450
    assert to_kilos(Decimal("2450")) == 2450


def test_a_negative_weight_is_refused() -> None:
    with pytest.raises(UnitError, match="cannot be negative"):
        to_kilos("-1")


def test_a_blank_weight_is_refused() -> None:
    with pytest.raises(UnitError, match="is blank"):
        to_kilos("   ")


def test_text_that_is_not_a_number_is_refused() -> None:
    with pytest.raises(UnitError, match="not a number"):
        to_kilos("heavy")


def test_a_boolean_is_not_a_weight() -> None:
    with pytest.raises(UnitError, match="true or false"):
        to_kilos(True)


def test_infinity_is_not_a_weight() -> None:
    with pytest.raises(UnitError, match="finite"):
        to_kilos(Decimal("Infinity"))


def test_the_name_of_the_quantity_reaches_the_message() -> None:
    with pytest.raises(UnitError, match="taxi fuel"):
        to_kilos("-4", what="taxi fuel")


def test_arms_keep_three_places_and_may_be_negative() -> None:
    assert to_metres("-1.2345") == Decimal("-1.235")
    assert to_metres("12.3456") == Decimal("12.346")


def test_index_keeps_one_place_and_may_be_negative() -> None:
    assert to_index("-4.55") == Decimal("-4.6")
    assert to_index("48.44") == Decimal("48.4")


def test_percentages_keep_one_place() -> None:
    assert to_percent("24.55") == Decimal("24.6")


def test_round_half_up_is_exported_for_the_schedules_to_use() -> None:
    assert round_half_up(Decimal("2.5"), KILO) == Decimal("3")
    assert round_half_up(Decimal("-2.5"), KILO) == Decimal("-3")
    assert round_half_up(Decimal("0.25"), INDEX_PLACES) == Decimal("0.3")


def test_a_weight_can_be_written_with_a_unit() -> None:
    assert parse_weight("1200") == 1200
    assert parse_weight("1200kg") == 1200
    assert parse_weight("1200 KG") == 1200


def test_tonnes_become_whole_kilos() -> None:
    assert parse_weight("1.2t") == 1200
    assert parse_weight("0.5 T") == 500


def test_weights_group_with_spaces_for_a_printed_report() -> None:
    assert format_kilos(12450) == "12 450"
    assert format_kilos(940) == "940"
    assert format_kilos(1234567) == "1 234 567"


def test_whole_weights_add_up() -> None:
    assert sum_kilos([1200, 340, 0]) == 1540
    assert sum_kilos([]) == 0


def test_adding_refuses_a_negative_member() -> None:
    with pytest.raises(UnitError, match="cannot be negative"):
        sum_kilos([1200, -1])
