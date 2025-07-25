from decimal import Decimal

import pytest

from holdtrim.errors import DataError, RuleError
from holdtrim.plan.lmc import Change, Changes, applied, check_tolerance
from holdtrim.plan.loadplan import Assignment, LoadPlan
from tests.fleet.test_type_store import a_type

KEY = "QH412/2025-05-12"


def plan(**weights: int) -> LoadPlan:
    return LoadPlan(
        flight_key=KEY,
        assignments=tuple(
            Assignment(position=code, weight=weight, destination="LGG")
            for code, weight in weights.items()
        ),
    )


def test_a_change_with_no_position_is_refused() -> None:
    with pytest.raises(DataError, match="needs a position"):
        Change(position=" ", weight=100)


def test_a_change_of_nothing_is_refused() -> None:
    with pytest.raises(DataError, match="is not a change"):
        Change(position="11P", weight=0)


def test_a_change_knows_which_way_it_went() -> None:
    assert Change(position="11P", weight=200).direction == "added"
    assert Change(position="11P", weight=-200).direction == "offloaded"


def test_a_change_describes_itself_for_the_box() -> None:
    change = Change(position="11P", weight=-200, what="two cartons")
    assert change.describe() == "offloaded 200 kg at 11P two cartons"


def test_a_change_with_no_description_still_reads() -> None:
    assert Change(position="11P", weight=200).describe() == "added 200 kg at 11P"


def test_the_net_and_the_total_are_not_the_same_thing() -> None:
    changes = Changes(
        changes=(Change(position="11P", weight=300), Change(position="21P", weight=-300))
    )
    assert changes.net == 0
    assert changes.total == 600


def test_changes_inside_the_tolerance_go_in_the_box() -> None:
    changes = Changes(changes=(Change(position="11P", weight=400),))
    assert changes.within_tolerance
    assert changes.over_by == 0


def test_three_small_changes_can_add_up_past_the_tolerance() -> None:
    changes = Changes(
        changes=(
            Change(position="11P", weight=200),
            Change(position="21P", weight=200),
            Change(position="51", weight=200),
        )
    )
    assert not changes.within_tolerance
    assert changes.over_by == 100


def test_a_tolerance_of_nothing_is_refused() -> None:
    with pytest.raises(DataError, match="has to be a weight"):
        Changes(tolerance=0)


def test_an_empty_set_of_changes_writes_none_in_the_box() -> None:
    assert Changes().empty
    assert Changes().lines() == ("none",)


def test_the_box_lists_every_change() -> None:
    changes = Changes(changes=(Change(position="11P", weight=200),))
    assert changes.lines() == ("added 200 kg at 11P",)


def test_adding_a_change_keeps_the_tolerance() -> None:
    changes = Changes(tolerance=300).add(Change(position="11P", weight=200))
    assert changes.tolerance == 300
    assert changes.total == 200


def test_loading_more_forward_pulls_the_index_down() -> None:
    changes = Changes(changes=(Change(position="11P", weight=500),))
    assert changes.index_change(a_type()) < Decimal("0")


def test_taking_weight_off_forward_pushes_the_index_up() -> None:
    changes = Changes(changes=(Change(position="11P", weight=-500),))
    assert changes.index_change(a_type()) > Decimal("0")


def test_no_changes_move_the_index_by_nothing() -> None:
    assert Changes().index_change(a_type()) == Decimal("0.0")


def test_a_change_is_worked_into_the_plan() -> None:
    changed = applied(plan(**{"11P": 2000}), Changes(changes=(Change(position="11P", weight=300),)))
    assert changed.weights == {"11P": 2300}


def test_an_offload_comes_off_the_plan() -> None:
    changed = applied(
        plan(**{"11P": 2000}), Changes(changes=(Change(position="11P", weight=-2000),))
    )
    assert changed.empty


def test_a_change_can_load_a_position_that_was_empty() -> None:
    changed = applied(plan(**{"11P": 2000}), Changes(changes=(Change(position="51", weight=300),)))
    assert changed.weights == {"11P": 2000, "51": 300}


def test_taking_off_more_than_is_there_is_refused() -> None:
    with pytest.raises(RuleError, match="only carrying 2000 kg"):
        applied(plan(**{"11P": 2000}), Changes(changes=(Change(position="11P", weight=-2500),)))


def test_the_uld_stays_with_the_position_through_a_change() -> None:
    started = LoadPlan(
        flight_key=KEY,
        assignments=(Assignment(position="11P", weight=2000, uld="PMC12345QH"),),
    )
    changed = applied(started, Changes(changes=(Change(position="11P", weight=-200),)))
    assert changed.at("11P").uld == "PMC12345QH"


def test_changes_past_the_tolerance_are_refused_with_the_reason() -> None:
    changes = Changes(changes=(Change(position="11P", weight=900),))
    with pytest.raises(RuleError, match="issue a new loadsheet"):
        check_tolerance(changes)


def test_changes_inside_the_tolerance_pass_the_check() -> None:
    check_tolerance(Changes(changes=(Change(position="11P", weight=200),)))
