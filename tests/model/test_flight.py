from datetime import date

import pytest

from holdtrim.errors import DataError
from holdtrim.ids import Flight
from holdtrim.model.flight import Sector


def sector(**changes: object) -> Sector:
    fields: dict[str, object] = {
        "designator": Flight(carrier="QH", number=412),
        "day": date(2025, 5, 12),
        "registration": "OY-JAF",
        "origin": "BLL",
        "destination": "LGG",
        "taxi_fuel": 90,
        "trip_fuel": 1450,
        "takeoff_fuel": 2600,
    }
    fields.update(changes)
    return Sector(**fields)  # type: ignore[arg-type]


def test_the_reference_is_the_designator_and_the_day_of_month() -> None:
    assert sector().reference == "QH412/12"


def test_the_key_carries_the_whole_date() -> None:
    assert sector().key == "QH412/2025-05-12"


def test_the_teletype_day_is_the_day_and_the_month_in_letters() -> None:
    assert sector().teletype_day == "12MAY"
    assert sector(day=date(2025, 1, 3)).teletype_day == "03JAN"


def test_the_route_reads_as_a_manifest_writes_it() -> None:
    assert sector().route == "BLLLGG"


def test_a_flight_going_nowhere_is_refused() -> None:
    with pytest.raises(DataError, match="to itself"):
        sector(destination="BLL")


def test_the_landing_fuel_is_what_is_left_after_the_trip() -> None:
    assert sector().landing_fuel == 1150


def test_the_block_fuel_includes_the_taxi_burn() -> None:
    assert sector().block_fuel == 2690


def test_carrying_less_fuel_than_the_trip_burns_is_refused() -> None:
    with pytest.raises(DataError, match="carries 1000 kg of fuel"):
        sector(takeoff_fuel=1000)


def test_negative_fuel_is_refused() -> None:
    with pytest.raises(DataError, match="cannot be negative"):
        sector(taxi_fuel=-10)


def test_a_flight_with_no_crew_is_refused() -> None:
    with pytest.raises(DataError, match="no crew on it"):
        sector(crew=0)


def test_an_unknown_status_is_refused() -> None:
    with pytest.raises(DataError, match="no status this build knows"):
        sector(status="somewhere over the sea")


def test_only_a_planned_flight_is_open() -> None:
    assert sector().open
    assert not sector(status="closed").open


def test_a_freighter_takes_cargo_aircraft_only_shipments() -> None:
    assert sector().takes_cargo_aircraft_only
    assert not sector(freighter=False).takes_cargo_aircraft_only


def test_a_flight_describes_itself_in_one_line() -> None:
    assert sector().describe() == "QH412/12 BLLLGG OY-JAF fuel 2600/1450 (planned)"
