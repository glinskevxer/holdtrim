import sqlite3
from collections.abc import Iterator
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.findings import STOP, WATCH, Finding
from holdtrim.ids import Flight
from holdtrim.model.flight import Sector
from holdtrim.model.tail import Tail
from holdtrim.office import read
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.report import exceptions
from holdtrim.report.exceptions import Against
from holdtrim.store import fleet, flights, plans, sheets
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened
from tests.fleet.test_type_store import a_type

DAY = date(2025, 5, 12)


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


def fly(conn: sqlite3.Connection, number: int = 412, weight: int = 2000) -> str:
    flights.add(
        conn,
        Sector(
            designator=Flight(carrier="QH", number=number),
            day=DAY,
            registration="OY-JAF",
            origin="BLL",
            destination="LGG",
            taxi_fuel=90,
            trip_fuel=1450,
            takeoff_fuel=2600,
        ),
    )
    key = f"QH{number}/{DAY.isoformat()}"
    plans.save(
        conn,
        LoadPlan(
            flight_key=key,
            assignments=(Assignment(position="11P", weight=weight, destination="LGG"),),
        ),
    )
    return key


def finish(conn: sqlite3.Connection, key: str) -> None:
    sheets.record(conn, sheets.from_sheet(read(conn, key).loadsheet("K Ravn"), DAY))
    flights.save(conn, replace(flights.get(conn, key), status="closed"))


def against(**changes: object) -> Against:
    fields: dict[str, object] = {
        "reference": "QH412/12",
        "key": "QH412/2025-05-12",
        "findings": (
            Finding(check="departure", where="QH412/12", detail="is still open", severity=WATCH),
        ),
    }
    fields.update(changes)
    return Against(**fields)  # type: ignore[arg-type]


def test_an_entry_counts_its_stops_and_its_notes() -> None:
    entry = against(
        findings=(
            Finding(check="departure", where="a", detail="one", severity=STOP),
            Finding(check="departure", where="b", detail="two", severity=WATCH),
        )
    )
    assert entry.stops == 1
    assert entry.notes == 1
    assert not entry.clean


def test_an_entry_prints_its_findings_under_it() -> None:
    lines = against().lines()
    assert lines[0] == "QH412/12 0 stopping, 1 note(s)"
    assert lines[1].strip().startswith("watch")


def test_a_day_with_nothing_flying_is_clean(conn: sqlite3.Connection) -> None:
    assert exceptions.against(conn, DAY) == ()
    assert exceptions.worst_first(()) == ("nothing is outstanding",)


def test_a_flight_with_no_loadsheet_is_outstanding(conn: sqlite3.Connection) -> None:
    fly(conn)
    report = exceptions.against(conn, DAY)
    assert report[0].reference == "QH412/12"
    assert report[0].stops >= 1


def test_a_finished_flight_is_not_outstanding(conn: sqlite3.Connection) -> None:
    finish(conn, fly(conn))
    assert exceptions.against(conn, DAY) == ()


def test_the_worst_flight_comes_first(conn: sqlite3.Connection) -> None:
    fly(conn, 412, weight=3400)
    finish(conn, fly(conn, 431))
    report = exceptions.against(conn, DAY)
    assert report[0].reference == "QH412/12"


def test_the_blocked_flights_are_named(conn: sqlite3.Connection) -> None:
    fly(conn)
    assert exceptions.blocked(exceptions.against(conn, DAY)) == ("QH412/12",)


def test_a_flight_with_only_notes_is_not_blocked(conn: sqlite3.Connection) -> None:
    key = fly(conn)
    sheets.record(conn, sheets.from_sheet(read(conn, key).loadsheet("K Ravn"), DAY))
    report = exceptions.against(conn, DAY)
    assert exceptions.blocked(report) == ()


def test_the_report_counts_what_is_stopping(conn: sqlite3.Connection) -> None:
    fly(conn)
    printed = exceptions.worst_first(exceptions.against(conn, DAY))
    assert "stopping across 1 flight(s)" in printed[-1]
