from datetime import date
from decimal import Decimal

from holdtrim.model.tail import Tail
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.plan.room import Room, best, everywhere, spare_in
from tests.fleet.test_type_store import a_type

KEY = "QH412/2025-05-12"
FUEL = (90, 1450, 2600)


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


def test_a_room_entry_describes_itself() -> None:
    entry = Room(position="11P", holding=2000, spare=900)
    assert entry.describe() == "11P holding 2000 kg, 900 kg more will go"
    assert not entry.full


def test_an_empty_position_takes_something() -> None:
    assert spare_in(a_type(), tail(), plan(), "11P", fuel=FUEL) > 0


def test_the_room_never_passes_the_position_limit() -> None:
    spare = spare_in(a_type(), tail(), plan(), "11P", fuel=FUEL)
    assert spare <= a_type().layout.position("11P").max_weight


def test_a_position_already_loaded_has_less_room() -> None:
    empty = spare_in(a_type(), tail(), plan(), "11P", fuel=FUEL)
    loaded = spare_in(a_type(), tail(), plan(**{"11P": 2000}), "11P", fuel=FUEL)
    assert loaded < empty


def test_a_combined_limit_cuts_the_room_down() -> None:
    alone = spare_in(a_type(), tail(), plan(), "21P", fuel=FUEL)
    beside = spare_in(a_type(), tail(), plan(**{"11P": 3000}), "21P", fuel=FUEL)
    assert beside < alone


def test_a_plan_that_is_already_illegal_has_no_room() -> None:
    assert spare_in(a_type(), tail(), plan(**{"11P": 3400}), "51", fuel=FUEL) == 0


def test_adding_the_room_keeps_the_plan_legal() -> None:
    from holdtrim.balance.limits import check
    from holdtrim.balance.loading import Balance, load_positions

    spare = spare_in(a_type(), tail(), plan(), "21P", fuel=FUEL)
    weights = {"21P": spare}
    balance = Balance(
        kind=a_type(),
        tail=tail(),
        loads=load_positions(a_type(), weights),
        taxi_fuel=90,
        trip_fuel=1450,
        takeoff_fuel=2600,
    )
    assert check(balance) == ()


def test_every_position_is_reported_most_room_first() -> None:
    report = everywhere(a_type(), tail(), plan(), fuel=FUEL)
    assert len(report) == 3
    assert [entry.spare for entry in report] == sorted(
        (entry.spare for entry in report), reverse=True
    )


def test_the_best_position_is_the_one_with_the_most_room() -> None:
    report = everywhere(a_type(), tail(), plan(), fuel=FUEL)
    assert best(report) == report[0].position


def test_a_flight_with_no_room_anywhere_says_so() -> None:
    report = everywhere(a_type(), tail(), plan(**{"11P": 3400}), fuel=FUEL)
    assert best(report) == ""


def test_a_report_with_nothing_in_it_has_no_best() -> None:
    assert best(()) == ""
