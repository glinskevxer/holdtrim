from decimal import Decimal

import pytest

from holdtrim.balance.index import (
    Contribution,
    arm_of_index,
    index_at_percent,
    index_of,
    percent_mac,
    shift,
    total_index,
)
from holdtrim.errors import DataError
from holdtrim.model.aircraft import MacGeometry


def geometry() -> MacGeometry:
    return MacGeometry(
        reference_arm=Decimal("12.615"),
        lemac=Decimal("11.409"),
        mac_length=Decimal("2.303"),
        index_constant=Decimal("1000"),
        index_reference=Decimal("50"),
    )


def test_a_load_at_the_reference_arm_moves_nothing() -> None:
    assert index_of(4000, Decimal("12.615"), geometry()) == Decimal("0.0")


def test_a_load_aft_of_the_reference_pushes_the_index_up() -> None:
    assert index_of(1000, Decimal("15.615"), geometry()) == Decimal("3.0")


def test_a_load_forward_of_the_reference_pulls_the_index_down() -> None:
    assert index_of(1000, Decimal("9.615"), geometry()) == Decimal("-3.0")


def test_the_index_scales_with_the_weight() -> None:
    single = index_of(1000, Decimal("15.615"), geometry())
    double = index_of(2000, Decimal("15.615"), geometry())
    assert double == single * 2


def test_contributions_add_on_to_the_starting_index() -> None:
    loads = [
        Contribution(label="11", weight=1000, arm=Decimal("9.615")),
        Contribution(label="41", weight=1000, arm=Decimal("15.615")),
    ]
    assert total_index(loads, geometry(), base=Decimal("50")) == Decimal("50.0")


def test_an_empty_load_leaves_the_starting_index_alone() -> None:
    assert total_index([], geometry(), base=Decimal("47.3")) == Decimal("47.3")


def test_a_contribution_reports_its_own_influence() -> None:
    load = Contribution(label="21", weight=2000, arm=Decimal("13.615"))
    assert load.influence(geometry()) == Decimal("2.0")


def test_index_and_arm_are_a_round_trip() -> None:
    arm = arm_of_index(10000, Decimal("60"), geometry())
    assert arm == Decimal("13.615")
    assert index_of(10000, arm, geometry()) + Decimal("50") == Decimal("60.0")


def test_reading_an_arm_at_zero_weight_is_refused() -> None:
    with pytest.raises(DataError, match="zero weight"):
        arm_of_index(0, Decimal("50"), geometry())


def test_the_index_reference_alone_sits_at_the_reference_arm() -> None:
    assert arm_of_index(15000, Decimal("50"), geometry()) == Decimal("12.615")


def test_percent_mac_reads_off_the_chord() -> None:
    assert percent_mac(15000, Decimal("50"), geometry()) == Decimal("52.4")


def test_a_percentage_converts_back_to_an_index() -> None:
    index = index_at_percent(15000, Decimal("52.4"), geometry())
    assert percent_mac(15000, index, geometry()) == Decimal("52.4")


def test_a_percentage_at_zero_weight_is_refused() -> None:
    with pytest.raises(DataError, match="zero weight"):
        index_at_percent(0, Decimal("25"), geometry())


def test_moving_a_load_aft_raises_the_index() -> None:
    assert shift(1000, Decimal("9.615"), Decimal("15.615"), geometry()) == Decimal("6.0")


def test_moving_a_load_back_where_it_was_undoes_it() -> None:
    there = shift(1400, Decimal("9.615"), Decimal("15.615"), geometry())
    back = shift(1400, Decimal("15.615"), Decimal("9.615"), geometry())
    assert there + back == Decimal("0.0")
