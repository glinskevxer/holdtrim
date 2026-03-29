from datetime import date
from decimal import Decimal

import pytest

from holdtrim.errors import DataError
from holdtrim.model.tail import Tail
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.plan.sequence import (
    as_planned,
    instruction,
    outside,
    suggested,
    unloading,
    walk,
)
from tests.fleet.test_type_store import a_type

KEY = "QH412/2025-05-12"


def tail() -> Tail:
    return Tail(
        registration="OY-JAF",
        type_code="AT7F",
        dry_operating_weight=13640,
        dry_operating_index=Decimal("46.2"),
        weighed_on=date(2024, 6, 18),
    )


def plan(**weights: int) -> LoadPlan:
    return LoadPlan(
        flight_key=KEY,
        assignments=tuple(
            Assignment(position=code, weight=weight, destination="LGG")
            for code, weight in weights.items()
        ),
    )


def test_walking_an_order_reports_a_step_for_each_position() -> None:
    steps = walk(a_type(), tail(), plan(**{"11P": 2000, "51": 300}).assignments)
    assert [step.position for step in steps] == ["11P", "51"]
    assert [step.order for step in steps] == [1, 2]


def test_the_running_weight_adds_up_as_it_goes() -> None:
    steps = walk(a_type(), tail(), plan(**{"11P": 2000, "51": 300}).assignments)
    assert steps[0].running_weight == 15640
    assert steps[1].running_weight == 15940


def test_a_sensible_order_stays_inside_all_the_way() -> None:
    steps = walk(a_type(), tail(), plan(**{"11P": 2000, "51": 300}).assignments)
    assert outside(steps) == ()


def test_loading_the_back_first_walks_out_of_the_envelope() -> None:
    loaded = plan(**{"51": 3000, "11P": 2500})
    steps = walk(a_type(), tail(), loaded.assignments)
    assert not steps[0].inside
    assert len(outside(steps)) == 1


def test_the_same_load_in_a_better_order_stays_inside() -> None:
    loaded = plan(**{"51": 3000, "11P": 2500})
    steps = walk(a_type(), tail(), suggested(a_type(), loaded))
    assert outside(steps) == ()


def test_the_suggested_order_runs_from_both_ends_inwards() -> None:
    loaded = plan(**{"11P": 900, "21P": 900, "51": 900})
    order = [entry.position for entry in suggested(a_type(), loaded)]
    assert order == ["11P", "51", "21P"]


def test_an_empty_plan_has_no_order() -> None:
    assert suggested(a_type(), plan()) == ()


def test_the_plan_order_is_whatever_it_was_written_in() -> None:
    loaded = plan(**{"51": 300, "11P": 2000})
    assert [entry.position for entry in as_planned(loaded)] == ["51", "11P"]


def test_unloading_is_the_reverse_of_loading() -> None:
    loaded = plan(**{"11P": 2000, "21P": 900, "51": 300})
    order = suggested(a_type(), loaded)
    assert [entry.position for entry in unloading(order)] == [
        entry.position for entry in reversed(order)
    ]


def test_the_instruction_is_one_line_a_step() -> None:
    steps = walk(a_type(), tail(), plan(**{"11P": 2000}).assignments)
    lines = instruction(steps)
    assert lines[0].startswith("1. 11P 2000 kg")
    assert "inside" in lines[0]


def test_a_step_outside_the_envelope_shouts() -> None:
    steps = walk(a_type(), tail(), plan(**{"51": 3000}).assignments)
    assert "OUTSIDE" in instruction(steps)[0]


def test_an_empty_instruction_is_refused() -> None:
    with pytest.raises(DataError, match="nothing to load"):
        instruction(())
