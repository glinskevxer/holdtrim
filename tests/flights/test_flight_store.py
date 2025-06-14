import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.errors import DuplicateError, NotFoundError, StateError
from holdtrim.ids import Flight
from holdtrim.model.flight import Sector
from holdtrim.model.tail import Tail
from holdtrim.store import fleet, flights
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened
from tests.fleet.test_type_store import a_type


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        fleet.add_type(connection, a_type())
        for registration in ("OY-JAF", "OY-JAG"):
            fleet.add_tail(
                connection,
                Tail(
                    registration=registration,
                    type_code="AT7F",
                    dry_operating_weight=13640,
                    dry_operating_index=Decimal("46.2"),
                    weighed_on=date(2024, 6, 18),
                ),
            )
        yield connection


def sector(number: int = 412, **changes: object) -> Sector:
    fields: dict[str, object] = {
        "designator": Flight(carrier="QH", number=number),
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


def test_a_flight_goes_on_file_and_comes_back(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector())
    assert flights.get(conn, "QH412/2025-05-12") == sector()


def test_a_flight_is_found_by_designator_and_day(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector())
    assert flights.find(conn, "qh412", date(2025, 5, 12)).registration == "OY-JAF"


def test_the_same_flight_twice_is_refused(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector())
    with pytest.raises(DuplicateError, match="already on file"):
        flights.add(conn, sector())


def test_a_flight_on_an_aeroplane_that_is_not_on_the_fleet(conn: sqlite3.Connection) -> None:
    with pytest.raises(StateError, match="not on the fleet"):
        flights.add(conn, sector(registration="OY-ZZZ"))


def test_asking_for_a_flight_that_is_not_on_file(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no flight QH999/2025-05-12"):
        flights.find(conn, "QH999", date(2025, 5, 12))


def test_the_programme_for_a_day_comes_back_in_number_order(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector(431))
    flights.add(conn, sector(412))
    assert [s.designator.number for s in flights.on_day(conn, date(2025, 5, 12))] == [412, 431]


def test_another_day_is_empty(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector())
    assert flights.on_day(conn, date(2025, 5, 13)) == []


def test_everything_one_aeroplane_flies_comes_back(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector(412))
    flights.add(conn, sector(431, registration="OY-JAG"))
    assert [s.designator.number for s in flights.for_tail(conn, "oy-jaf")] == [412]


def test_the_departures_from_a_station_come_back(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector(412))
    flights.add(conn, sector(431, origin="LGG", destination="BLL"))
    out = flights.out_of(conn, "BLL", date(2025, 5, 12))
    assert [s.designator.number for s in out] == [412]


def test_only_the_open_flights_come_back(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector(412))
    flights.add(conn, sector(431, status="closed"))
    assert [s.designator.number for s in flights.still_open(conn, date(2025, 5, 12))] == [412]


def test_saving_records_a_change_of_fuel(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector())
    flights.save(conn, sector(trip_fuel=1600))
    assert flights.get(conn, "QH412/2025-05-12").landing_fuel == 1000


def test_saving_a_flight_that_was_never_filed_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no flight"):
        flights.save(conn, sector())


def test_removing_takes_it_off_file(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector())
    flights.remove(conn, "QH412/2025-05-12")
    assert not flights.exists(conn, "QH412/2025-05-12")
    assert flights.count(conn) == 0


def test_removing_one_that_is_not_there_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no flight"):
        flights.remove(conn, "QH412/2025-05-12")


def test_everything_on_file_lists_oldest_first(conn: sqlite3.Connection) -> None:
    flights.add(conn, sector(412, day=date(2025, 5, 13)))
    flights.add(conn, sector(412))
    assert [s.day.day for s in flights.listing(conn)] == [12, 13]
