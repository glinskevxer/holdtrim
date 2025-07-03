from datetime import date
from decimal import Decimal

import pytest

from holdtrim.errors import DataError
from holdtrim.model.tail import Tail
from holdtrim.plan.allocate import Item, allocate, for_flight, target_index
from tests.fleet.test_type_store import a_type


def tail() -> Tail:
    return Tail(
        registration="OY-JAF",
        type_code="AT7F",
        dry_operating_weight=13640,
        dry_operating_index=Decimal("46.2"),
        weighed_on=date(2024, 6, 18),
    )


def pallet(label: str, weight: int) -> Item:
    return Item(label=label, weight=weight, base="PMC", destination="LGG")


def test_an_item_with_no_weight_is_refused() -> None:
    with pytest.raises(DataError, match="weighs nothing"):
        Item(label="PMC12345QH", weight=0, base="PMC")


def test_an_item_with_no_base_is_loose() -> None:
    assert Item(label="", weight=300).loose


def test_the_target_is_the_middle_of_the_zero_fuel_envelope() -> None:
    assert target_index(a_type(), 13000) == Decimal("48.0")


def test_the_target_clamps_to_the_ends_of_the_envelope() -> None:
    assert target_index(a_type(), 1000) == target_index(a_type(), 13000)
    assert target_index(a_type(), 99000) == target_index(a_type(), 20800)


def test_one_pallet_goes_in_a_position_that_takes_it() -> None:
    made = allocate(a_type(), tail(), (pallet("PMC12345QH", 2000),))
    assert made.complete
    assert made.plan.at(made.plan.positions[0]).uld == "PMC12345QH"


def test_a_pallet_never_goes_in_a_bulk_position() -> None:
    made = allocate(a_type(), tail(), (pallet("PMC12345QH", 2000),))
    assert made.plan.positions[0] in {"11P", "21P"}


def test_loose_cargo_goes_in_the_bulk_position() -> None:
    made = allocate(a_type(), tail(), (Item(label="", weight=300),))
    assert made.plan.positions == ("51",)


def test_two_pallets_take_two_positions() -> None:
    made = allocate(a_type(), tail(), (pallet("PMC12345QH", 2000), pallet("PMC12346QH", 1500)))
    assert made.complete
    assert len(made.plan.positions) == 2


def test_the_heaviest_pallet_is_placed_first() -> None:
    made = allocate(a_type(), tail(), (pallet("PMC12345QH", 900), pallet("PMC12346QH", 2400)))
    assert made.plan.assignments[0].uld == "PMC12346QH"


def test_more_pallets_than_positions_leaves_one_behind() -> None:
    items = (
        pallet("PMC12345QH", 2000),
        pallet("PMC12346QH", 1800),
        pallet("PMC12347QH", 1600),
    )
    made = allocate(a_type(), tail(), items)
    assert not made.complete
    assert made.reason_for("PMC12347QH") == "no free position takes that base size"


def test_something_too_heavy_for_any_position_is_left_behind() -> None:
    made = allocate(a_type(), tail(), (pallet("PMC12345QH", 3400),))
    assert made.reason_for("PMC12345QH") == "every free position that takes it is too small"


def test_a_pair_that_would_break_the_combined_limit_is_left_behind() -> None:
    items = (pallet("PMC12345QH", 3100), pallet("PMC12346QH", 3100))
    made = allocate(a_type(), tail(), items)
    assert made.reason_for("PMC12346QH") == "it would break a combined limit wherever it went"


def test_asking_why_something_that_was_placed_failed_is_refused() -> None:
    made = allocate(a_type(), tail(), (pallet("PMC12345QH", 2000),))
    with pytest.raises(DataError, match="was placed, or was never offered"):
        made.reason_for("PMC12345QH")


def test_a_loose_load_with_nowhere_to_go_is_left_behind() -> None:
    items = (Item(label="A", weight=300), Item(label="B", weight=200))
    made = allocate(a_type(), tail(), items)
    assert made.reason_for("B") == "no free position takes that base size"


def test_the_plan_can_be_labelled_with_a_flight() -> None:
    made = for_flight("QH412/2025-05-12", a_type(), tail(), (pallet("PMC12345QH", 2000),))
    assert made.plan.flight_key == "QH412/2025-05-12"


def test_an_allocation_with_nothing_offered_is_empty_and_complete() -> None:
    made = allocate(a_type(), tail(), ())
    assert made.complete
    assert made.plan.empty
