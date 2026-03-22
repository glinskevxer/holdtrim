import pytest

from holdtrim.errors import DataError
from holdtrim.plan.offload import (
    CONTRACT,
    GENERAL,
    PRIORITY,
    STANDBY,
    Candidate,
    Offload,
    choose,
    excess,
    for_balance,
)
from tests.balance.test_loading import balance


def candidate(position: str, weight: int, priority: int = GENERAL, **changes: object) -> Candidate:
    fields: dict[str, object] = {"position": position, "weight": weight, "priority": priority}
    fields.update(changes)
    return Candidate(**fields)  # type: ignore[arg-type]


def test_a_candidate_with_no_weight_is_refused() -> None:
    with pytest.raises(DataError, match="nothing in 11P to take off"):
        candidate("11P", 0)


def test_a_priority_this_build_does_not_know_is_refused() -> None:
    with pytest.raises(DataError, match="not a priority"):
        candidate("11P", 100, priority=9)


def test_a_candidate_is_labelled_by_its_device_first() -> None:
    assert candidate("11P", 100, uld="PMC12345QH", awb="125-1").label == "PMC12345QH"
    assert candidate("11P", 100, awb="125-1").label == "125-1"
    assert candidate("11P", 100).label == "11P"


def test_a_candidate_describes_itself() -> None:
    assert candidate("11P", 900, uld="PMC12345QH").describe() == ("PMC12345QH from 11P, 900 kg")


def test_nothing_to_take_off_takes_nothing() -> None:
    made = choose((candidate("11P", 900),), 0)
    assert made.removed == ()
    assert made.enough
    assert made.describe() == "nothing to offload"


def test_the_lowest_promise_goes_first() -> None:
    made = choose(
        (
            candidate("11P", 900, priority=PRIORITY),
            candidate("21P", 900, priority=STANDBY),
        ),
        500,
    )
    assert [item.position for item in made.removed] == ["21P"]


def test_the_heaviest_goes_first_within_a_promise() -> None:
    made = choose((candidate("11P", 400), candidate("21P", 900)), 500)
    assert [item.position for item in made.removed] == ["21P"]


def test_more_comes_off_than_strictly_has_to() -> None:
    made = choose((candidate("11P", 900),), 500)
    assert made.enough
    assert made.spare == 400


def test_two_items_come_off_when_one_is_not_enough() -> None:
    made = choose((candidate("11P", 400), candidate("21P", 300)), 600)
    assert len(made.removed) == 2
    assert made.enough


def test_not_enough_on_board_to_offload_is_reported() -> None:
    made = choose((candidate("11P", 400),), 900)
    assert not made.enough
    assert made.short_by == 500


def test_an_empty_offload_weighs_nothing() -> None:
    assert Offload().weight == 0
    assert Offload().enough


def test_a_flight_inside_its_limits_has_no_excess() -> None:
    assert excess(balance({"11P": 2000})) == 0


def test_a_flight_over_its_limits_has_an_excess() -> None:
    assert excess(balance({"11P": 3175, "21P": 3175, "51": 3175}, takeoff_fuel=1600)) > 0


def test_the_offload_for_a_balance_takes_the_excess_off() -> None:
    figures = balance({"11P": 3175, "21P": 3175, "51": 3175}, takeoff_fuel=1600)
    made = for_balance(
        figures,
        (
            candidate("11P", 3175, priority=CONTRACT),
            candidate("21P", 3175, priority=STANDBY),
            candidate("51", 3175, priority=GENERAL),
        ),
    )
    assert made.enough
    assert made.removed[0].position == "21P"


def test_a_flight_inside_its_limits_offloads_nothing() -> None:
    made = for_balance(balance({"11P": 2000}), (candidate("11P", 2000),))
    assert made.removed == ()
