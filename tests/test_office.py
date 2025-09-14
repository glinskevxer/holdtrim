import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.errors import NotFoundError, StateError
from holdtrim.ids import Flight
from holdtrim.model.flight import Sector
from holdtrim.model.tail import Tail
from holdtrim.office import Office, read
from holdtrim.plan.lmc import Change, Changes
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.store import fleet, flights, plans
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened
from tests.fleet.test_type_store import a_type

KEY = "QH412/2025-05-12"


def tail(**changes: object) -> Tail:
    fields: dict[str, object] = {
        "registration": "OY-JAF",
        "type_code": "AT7F",
        "dry_operating_weight": 13640,
        "dry_operating_index": Decimal("46.2"),
        "weighed_on": date(2024, 6, 18),
    }
    fields.update(changes)
    return Tail(**fields)  # type: ignore[arg-type]


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        fleet.add_type(connection, a_type())
        fleet.add_tail(connection, tail())
        flights.add(
            connection,
            Sector(
                designator=Flight(carrier="QH", number=412),
                day=date(2025, 5, 12),
                registration="OY-JAF",
                origin="BLL",
                destination="LGG",
                taxi_fuel=90,
                trip_fuel=1450,
                takeoff_fuel=2600,
            ),
        )
        yield connection


def planned(conn: sqlite3.Connection) -> None:
    plans.save(
        conn,
        LoadPlan(
            flight_key=KEY,
            assignments=(
                Assignment(position="11P", weight=2000, uld="PMC12345QH", destination="LGG"),
            ),
        ),
    )


def test_a_flight_file_gathers_the_four_records(conn: sqlite3.Connection) -> None:
    file = read(conn, KEY)
    assert file.sector.registration == "OY-JAF"
    assert file.tail.type_code == "AT7F"
    assert file.kind.code == "AT7F"
    assert file.plan.empty


def test_the_file_keys_off_the_flight(conn: sqlite3.Connection) -> None:
    assert read(conn, KEY).key == KEY


def test_a_flight_that_is_not_on_file_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no flight"):
        read(conn, "QH999/2025-05-12")


def test_the_plan_becomes_loads_the_balance_can_use(conn: sqlite3.Connection) -> None:
    planned(conn)
    file = read(conn, KEY)
    assert file.loads[0].position.code == "11P"
    assert file.loads[0].label == "PMC12345QH"


def test_the_balance_reads_off_the_flight_and_the_plan(conn: sqlite3.Connection) -> None:
    planned(conn)
    figures = read(conn, KEY).balance()
    assert figures.payload == 2000
    assert figures.takeoff.weight == 18240


def test_the_loadsheet_comes_out_of_the_same_file(conn: sqlite3.Connection) -> None:
    planned(conn)
    sheet = read(conn, KEY).loadsheet("K Ravn")
    assert sheet.reference == "QH412/12 OY-JAF edition 1"
    assert sheet.payload == 2000


def test_last_minute_changes_can_be_handed_to_the_sheet(conn: sqlite3.Connection) -> None:
    planned(conn)
    changes = Changes(changes=(Change(position="11P", weight=-200),))
    sheet = read(conn, KEY).loadsheet("K Ravn", changes=changes)
    assert sheet.changes.total == 200


def test_an_aeroplane_out_of_service_cannot_be_loaded(conn: sqlite3.Connection) -> None:
    fleet.save_tail(conn, tail(status="maintenance"))
    with pytest.raises(StateError, match="maintenance and cannot be loaded"):
        read(conn, KEY).check_flyable()


def test_an_expired_weighing_stops_the_flight(conn: sqlite3.Connection) -> None:
    fleet.save_tail(conn, tail(weighed_on=date(2018, 1, 2)))
    with pytest.raises(StateError, match="expired on"):
        read(conn, KEY).check_flyable()


def test_a_serviceable_aeroplane_with_a_current_weighing_passes(
    conn: sqlite3.Connection,
) -> None:
    read(conn, KEY).check_flyable()


def test_the_office_finds_a_flight_by_designator_and_day(conn: sqlite3.Connection) -> None:
    office = Office(connection=conn)
    assert office.on("qh412", date(2025, 5, 12)).key == KEY


def test_the_office_reads_a_flight_once(conn: sqlite3.Connection) -> None:
    office = Office(connection=conn)
    first = office.flight(KEY)
    assert office.flight(KEY) is first


def test_forgetting_a_flight_reads_it_again(conn: sqlite3.Connection) -> None:
    office = Office(connection=conn)
    first = office.flight(KEY)
    office.forget(KEY)
    assert office.flight(KEY) is not first
