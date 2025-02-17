from decimal import Decimal

import pytest

from holdtrim.errors import DataError, NotFoundError
from holdtrim.model.hold import CumulativeLimit, HoldLayout
from holdtrim.model.position import Position


def position(code: str, arm: str, compartment: str = "MAIN", **changes: object) -> Position:
    fields: dict[str, object] = {
        "code": code,
        "compartment": compartment,
        "arm": Decimal(arm),
        "max_weight": 3175,
        "length": Decimal("3.175"),
        "width": Decimal("2.235"),
        "max_running_load": 1200,
        "max_area_load": 732,
        "accepts": ("PMC",),
    }
    fields.update(changes)
    return Position(**fields)  # type: ignore[arg-type]


def layout() -> HoldLayout:
    return HoldLayout(
        positions=(
            position("11P", "9.400"),
            position("21P", "12.600"),
            position("31P", "15.800"),
            position("51", "18.100", compartment="BULK", accepts=()),
        ),
        cumulative=(
            CumulativeLimit(label="11P and 21P", positions=("11P", "21P"), max_weight=5400),
        ),
    )


def test_a_limit_needs_at_least_two_positions() -> None:
    with pytest.raises(DataError, match="fewer than two positions"):
        CumulativeLimit(label="one", positions=("11P",), max_weight=5400)


def test_a_limit_naming_a_position_twice_is_refused() -> None:
    with pytest.raises(DataError, match="names a position twice"):
        CumulativeLimit(label="twice", positions=("11P", "11P"), max_weight=5400)


def test_a_limit_with_no_label_is_refused() -> None:
    with pytest.raises(DataError, match="needs a label"):
        CumulativeLimit(label="  ", positions=("11P", "21P"), max_weight=5400)


def test_a_limit_with_no_weight_is_refused() -> None:
    with pytest.raises(DataError, match="has no weight"):
        CumulativeLimit(label="pair", positions=("11P", "21P"), max_weight=0)


def test_a_limit_knows_which_positions_it_watches() -> None:
    limit = CumulativeLimit(label="pair", positions=("11P", "21P"), max_weight=5400)
    assert limit.covers("11p")
    assert not limit.covers("31P")


def test_a_pair_inside_the_shared_limit_is_over_by_nothing() -> None:
    limit = CumulativeLimit(label="pair", positions=("11P", "21P"), max_weight=5400)
    assert limit.over_by({"11P": 2700, "21P": 2700}) == 0


def test_two_legal_positions_can_break_their_shared_limit() -> None:
    limit = CumulativeLimit(label="pair", positions=("11P", "21P"), max_weight=5400)
    assert limit.over_by({"11P": 3175, "21P": 3175}) == 950


def test_positions_not_loaded_count_as_nothing() -> None:
    limit = CumulativeLimit(label="pair", positions=("11P", "21P"), max_weight=5400)
    assert limit.over_by({"11P": 3175}) == 0


def test_a_layout_with_no_positions_is_refused() -> None:
    with pytest.raises(DataError, match="not a layout"):
        HoldLayout(positions=())


def test_two_positions_sharing_a_code_are_refused() -> None:
    with pytest.raises(DataError, match="share a code"):
        HoldLayout(positions=(position("11P", "9.400"), position("11P", "12.600")))


def test_a_limit_naming_a_position_outside_the_layout_is_refused() -> None:
    with pytest.raises(DataError, match="not in the layout"):
        HoldLayout(
            positions=(position("11P", "9.400"), position("21P", "12.600")),
            cumulative=(CumulativeLimit(label="pair", positions=("11P", "99X"), max_weight=5400),),
        )


def test_a_position_comes_back_by_code() -> None:
    assert layout().position("21p").arm == Decimal("12.600")


def test_asking_for_a_position_that_is_not_there() -> None:
    with pytest.raises(NotFoundError, match="no position 99X"):
        layout().position("99X")


def test_the_layout_lists_its_codes_and_answers_whether_it_has_one() -> None:
    assert layout().codes == ("11P", "21P", "31P", "51")
    assert layout().has("51")
    assert not layout().has("61")


def test_capacity_is_the_sum_of_the_position_limits() -> None:
    assert layout().capacity == 3175 * 4


def test_positions_come_back_by_compartment() -> None:
    assert [p.code for p in layout().in_compartment("bulk")] == ["51"]


def test_an_unknown_compartment_is_refused() -> None:
    with pytest.raises(DataError, match="no compartment called"):
        layout().in_compartment("TAIL")


def test_positions_sort_front_to_back() -> None:
    assert [p.code for p in layout().by_arm()] == ["11P", "21P", "31P", "51"]


def test_the_arm_span_runs_from_the_first_position_to_the_last() -> None:
    assert layout().arm_span() == (Decimal("9.400"), Decimal("18.100"))


def test_the_limits_touching_a_position_come_back() -> None:
    assert [limit.label for limit in layout().limits_touching("11P")] == ["11P and 21P"]
    assert layout().limits_touching("51") == ()


def test_the_positions_that_take_a_base_come_back_front_to_back() -> None:
    assert [p.code for p in layout().accepting("pmc")] == ["11P", "21P", "31P"]
