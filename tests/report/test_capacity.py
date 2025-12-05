import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.ids import Flight
from holdtrim.model.flight import Sector
from holdtrim.model.tail import Tail
from holdtrim.office import read
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.report import capacity
from holdtrim.report.capacity import Capacity
from holdtrim.store import fleet, flights, plans
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened
from tests.fleet.test_type_store import a_type

KEY = "QH412/2025-05-12"


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        fleet.add_type(connection, a_type())
        fleet.add_tail(
            connection,
            Tail(
                registration="OY-JAF",
                type_code="AT7F",
                dry_operating_weight=13640,
                dry_operating_index=Decimal("46.2"),
                weighed_on=date(2024, 6, 18),
            ),
        )
        yield connection


def file_a_flight(conn: sqlite3.Connection, number: int = 412) -> None:
    flights.add(
        conn,
        Sector(
            designator=Flight(carrier="QH", number=number),
            day=date(2025, 5, 12),
            registration="OY-JAF",
            origin="BLL",
            destination="LGG",
            taxi_fuel=90,
            trip_fuel=1450,
            takeoff_fuel=2600,
        ),
    )


def plan_it(conn: sqlite3.Connection, key: str = KEY, weight: int = 2000) -> None:
    plans.save(
        conn,
        LoadPlan(
            flight_key=key,
            assignments=(Assignment(position="11P", weight=weight, destination="LGG"),),
        ),
    )


def entry(**changes: object) -> Capacity:
    fields: dict[str, object] = {
        "flight_key": KEY,
        "reference": "QH412/12",
        "registration": "OY-JAF",
        "route": "BLLLGG",
        "payload": 2000,
        "underload": 2000,
        "limited_by": "takeoff",
        "positions_used": 1,
        "positions_total": 3,
        "findings": 0,
    }
    fields.update(changes)
    return Capacity(**fields)  # type: ignore[arg-type]


def test_the_free_positions_are_what_is_left() -> None:
    assert entry().positions_free == 2


def test_what_was_offered_is_payload_plus_underload() -> None:
    assert entry().offered == 4000


def test_utilisation_reads_as_a_percentage() -> None:
    assert entry().weight_utilisation == Decimal("50.0")
    assert entry().position_utilisation == Decimal("33.3")


def test_an_empty_flight_reads_zero_rather_than_dividing_by_nothing() -> None:
    assert entry(payload=0, underload=0).weight_utilisation == Decimal("0.0")
    assert entry(positions_total=0).position_utilisation == Decimal("0.0")


def test_a_flight_with_no_underload_is_full_by_weight() -> None:
    assert entry(underload=0).full_by_weight
    assert not entry().full_by_weight


def test_a_flight_using_every_position_is_full_by_position() -> None:
    assert entry(positions_used=3).full_by_position
    assert not entry().full_by_position


def test_a_capacity_describes_itself() -> None:
    line = entry().describe()
    assert "QH412/12 BLLLGG 2000 kg" in line
    assert "1/3 positions" in line


def test_a_flight_reads_its_capacity_off_its_file(conn: sqlite3.Connection) -> None:
    file_a_flight(conn)
    plan_it(conn)
    found = capacity.for_flight(read(conn, KEY))
    assert found.payload == 2000
    assert found.positions_used == 1
    assert found.positions_total == 3
    assert found.findings == 0


def test_an_illegal_plan_shows_its_findings(conn: sqlite3.Connection) -> None:
    file_a_flight(conn)
    plan_it(conn, weight=3400)
    assert capacity.for_flight(read(conn, KEY)).findings > 0


def test_a_day_programme_reads_every_flight(conn: sqlite3.Connection) -> None:
    file_a_flight(conn, 412)
    file_a_flight(conn, 431)
    plan_it(conn, "QH412/2025-05-12")
    plan_it(conn, "QH431/2025-05-12", weight=900)
    report = capacity.programme(conn, date(2025, 5, 12))
    assert [found.reference for found in report] == ["QH412/12", "QH431/12"]


def test_a_day_with_nothing_on_it_reports_nothing(conn: sqlite3.Connection) -> None:
    assert capacity.programme(conn, date(2025, 5, 13)) == ()


def test_the_carried_and_spare_totals_add_up(conn: sqlite3.Connection) -> None:
    file_a_flight(conn, 412)
    file_a_flight(conn, 431)
    plan_it(conn, "QH412/2025-05-12")
    plan_it(conn, "QH431/2025-05-12", weight=900)
    report = capacity.programme(conn, date(2025, 5, 12))
    assert capacity.carried(report) == 2900
    assert capacity.spare(report) > 0


def test_the_binding_limits_are_counted(conn: sqlite3.Connection) -> None:
    file_a_flight(conn)
    plan_it(conn)
    report = capacity.programme(conn, date(2025, 5, 12))
    counted = capacity.limits_biting(report)
    assert sum(counted.values()) == 1
