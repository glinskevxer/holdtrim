import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.errors import DataError
from holdtrim.ids import Flight
from holdtrim.model.flight import Sector
from holdtrim.model.tail import Tail
from holdtrim.office import read
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.report import season
from holdtrim.report.season import Period, Summary
from holdtrim.store import fleet, flights, plans, sheets
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened
from tests.fleet.test_type_store import a_type


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


def fly(conn: sqlite3.Connection, day: date, number: int = 412, weight: int = 2000) -> str:
    flights.add(
        conn,
        Sector(
            designator=Flight(carrier="QH", number=number),
            day=day,
            registration="OY-JAF",
            origin="BLL",
            destination="LGG",
            taxi_fuel=90,
            trip_fuel=1450,
            takeoff_fuel=2600,
        ),
    )
    key = f"QH{number}/{day.isoformat()}"
    plans.save(
        conn,
        LoadPlan(
            flight_key=key,
            assignments=(Assignment(position="11P", weight=weight, destination="LGG"),),
        ),
    )
    return key


def summary(**changes: object) -> Summary:
    fields: dict[str, object] = {
        "period": Period(start=date(2025, 5, 1), end=date(2025, 5, 31)),
        "flights": 2,
        "carried": 4000,
        "spare": 4000,
        "findings": 0,
        "issued": 2,
        "limits": {"takeoff": 2},
    }
    fields.update(changes)
    return Summary(**fields)  # type: ignore[arg-type]


def test_a_period_counts_both_ends() -> None:
    assert Period(start=date(2025, 5, 1), end=date(2025, 5, 3)).days == 3


def test_a_period_that_ends_before_it_starts_is_refused() -> None:
    with pytest.raises(DataError, match="cannot end on"):
        Period(start=date(2025, 5, 3), end=date(2025, 5, 1))


def test_a_period_lists_its_dates() -> None:
    dates = Period(start=date(2025, 5, 1), end=date(2025, 5, 3)).dates()
    assert [day.day for day in dates] == [1, 2, 3]


def test_a_period_describes_itself() -> None:
    line = Period(start=date(2025, 5, 1), end=date(2025, 5, 3)).describe()
    assert line == "2025-05-01 to 2025-05-03, 3 day(s)"


def test_the_average_payload_divides_by_the_flights() -> None:
    assert summary().average_payload == 2000


def test_a_period_with_no_flights_averages_nothing() -> None:
    assert summary(flights=0, carried=0).average_payload == 0


def test_utilisation_reads_as_a_percentage() -> None:
    assert summary().utilisation == Decimal("50.0")


def test_a_period_that_carried_nothing_reads_zero() -> None:
    assert summary(carried=0, spare=0).utilisation == Decimal("0.0")


def test_the_binding_limit_is_the_one_that_bound_most() -> None:
    assert summary(limits={"takeoff": 3, "zero fuel": 1}).binding == "takeoff"
    assert summary(limits={}).binding == ""


def test_the_summary_prints_its_figures() -> None:
    printed = summary().lines()
    assert "flights 2" in printed
    assert "carried 4000 kg" in printed
    assert "limited by takeoff on 2 flight(s)" in printed


def test_a_period_gathers_every_flight_in_it(conn: sqlite3.Connection) -> None:
    fly(conn, date(2025, 5, 12), 412)
    fly(conn, date(2025, 5, 13), 431)
    covered = Period(start=date(2025, 5, 12), end=date(2025, 5, 13))
    assert len(season.flights_in(conn, covered)) == 2


def test_a_flight_outside_the_period_is_left_out(conn: sqlite3.Connection) -> None:
    fly(conn, date(2025, 5, 20))
    covered = Period(start=date(2025, 5, 12), end=date(2025, 5, 13))
    assert season.flights_in(conn, covered) == ()


def test_a_period_adds_up_what_was_carried(conn: sqlite3.Connection) -> None:
    fly(conn, date(2025, 5, 12), 412, weight=2000)
    fly(conn, date(2025, 5, 13), 431, weight=900)
    covered = Period(start=date(2025, 5, 12), end=date(2025, 5, 13))
    found = season.summarise(conn, covered)
    assert found.flights == 2
    assert found.carried == 2900
    assert found.spare > 0


def test_the_loadsheets_issued_in_the_period_are_counted(conn: sqlite3.Connection) -> None:
    key = fly(conn, date(2025, 5, 12))
    sheets.record(conn, sheets.from_sheet(read(conn, key).loadsheet("K Ravn"), date(2025, 5, 12)))
    covered = Period(start=date(2025, 5, 12), end=date(2025, 5, 13))
    assert season.summarise(conn, covered).issued == 1


def test_an_empty_period_sums_to_nothing(conn: sqlite3.Connection) -> None:
    covered = Period(start=date(2025, 5, 12), end=date(2025, 5, 13))
    found = season.summarise(conn, covered)
    assert found.flights == 0
    assert found.utilisation == Decimal("0.0")
