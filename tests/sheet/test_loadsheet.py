from datetime import date
from decimal import Decimal

import pytest

from holdtrim.balance.loading import Balance, load_positions
from holdtrim.errors import RuleError
from holdtrim.ids import Flight
from holdtrim.model.flight import Sector
from holdtrim.model.tail import Tail
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.sheet.loadsheet import Loadsheet
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


def sector() -> Sector:
    return Sector(
        designator=Flight(carrier="QH", number=412),
        day=date(2025, 5, 12),
        registration="OY-JAF",
        origin="BLL",
        destination="LGG",
        taxi_fuel=90,
        trip_fuel=1450,
        takeoff_fuel=2600,
    )


def sheet(weights: dict[str, int] | None = None, **changes: object) -> Loadsheet:
    kind = a_type()
    loaded = weights if weights is not None else {"11P": 2000, "51": 300}
    plan = LoadPlan(
        flight_key=KEY,
        assignments=tuple(
            Assignment(position=code, weight=weight, destination="LGG")
            for code, weight in loaded.items()
        ),
    )
    balance = Balance(
        kind=kind,
        tail=tail(),
        loads=load_positions(kind, loaded),
        taxi_fuel=90,
        trip_fuel=1450,
        takeoff_fuel=2600,
    )
    fields: dict[str, object] = {
        "sector": sector(),
        "tail": tail(),
        "kind": kind,
        "plan": plan,
        "balance": balance,
        "prepared_by": "K Ravn",
    }
    fields.update(changes)
    return Loadsheet(**fields)  # type: ignore[arg-type]


def test_the_sheet_names_itself() -> None:
    assert sheet().reference == "QH412/12 OY-JAF edition 1"


def test_the_dry_operating_weight_comes_off_the_tail() -> None:
    assert sheet().dry_operating_weight == 13640


def test_the_payload_is_everything_loaded() -> None:
    assert sheet().payload == 2300


def test_the_distribution_groups_by_compartment() -> None:
    assert sheet().by_compartment == {"MAIN": 2000, "BULK": 300}


def test_the_distribution_groups_by_offload_point() -> None:
    assert sheet().by_destination == {"LGG": 2300}


def test_an_assignment_with_no_destination_goes_to_the_flight_destination() -> None:
    plan = LoadPlan(flight_key=KEY, assignments=(Assignment(position="11P", weight=2000),))
    assert sheet(plan=plan).by_destination == {"LGG": 2000}


def test_the_three_centres_of_gravity_read_off_the_conditions() -> None:
    made = sheet()
    assert made.zero_fuel_percent_mac == made.balance.zero_fuel.percent_mac(a_type())
    assert made.takeoff_percent_mac == made.balance.takeoff.percent_mac(a_type())
    assert made.landing_percent_mac == made.balance.landing.percent_mac(a_type())


def test_the_trim_setting_comes_off_the_takeoff_centre_of_gravity() -> None:
    made = sheet()
    assert made.trim_setting == a_type().trim.setting_at(made.takeoff_percent_mac)


def test_the_underload_and_the_limiting_weight_come_off_the_balance() -> None:
    made = sheet()
    assert made.underload == made.balance.underload
    assert made.limiting_weight in {"zero fuel", "takeoff", "landing"}


def test_a_good_sheet_is_signable_and_issues() -> None:
    made = sheet()
    assert made.findings == ()
    assert made.signable
    assert made.issue() is made


def test_a_sheet_with_a_finding_will_not_issue() -> None:
    made = sheet({"11P": 3400})
    assert not made.signable
    with pytest.raises(RuleError, match="cannot be issued"):
        made.issue()


def test_reissuing_moves_both_editions_on() -> None:
    again = sheet().reissued()
    assert again.edition == 2
    assert again.plan.edition == 2
    assert again.reference.endswith("edition 2")


def test_the_summary_carries_the_figures_a_handover_needs() -> None:
    line = sheet().summary()
    assert "ZFW 15940" in line
    assert "TOW 18540" in line
    assert "trim" in line
