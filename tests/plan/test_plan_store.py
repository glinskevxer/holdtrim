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
from holdtrim.plan.loadplan import Assignment, LoadPlan
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


def plan(*assignments: Assignment, edition: int = 1) -> LoadPlan:
    return LoadPlan(flight_key=KEY, assignments=assignments, edition=edition)


def pallet(position: str = "11P", uld: str = "PMC12345QH") -> Assignment:
    return Assignment(position=position, weight=2000, uld=uld, destination="LGG")


def test_a_plan_is_written_and_read_back(conn: sqlite3.Connection) -> None:
    plans.save(conn, plan(pallet()))
    assert plans.get(conn, KEY) == plan(pallet())


def test_the_assignments_keep_their_order(conn: sqlite3.Connection) -> None:
    plans.save(conn, plan(pallet("21P", "PMC12346QH"), pallet()))
    assert plans.get(conn, KEY).positions == ("21P", "11P")


def test_writing_again_replaces_what_was_there(conn: sqlite3.Connection) -> None:
    plans.save(conn, plan(pallet(), pallet("21P", "PMC12346QH")))
    plans.save(conn, plan(pallet(), edition=2))
    read = plans.get(conn, KEY)
    assert read.positions == ("11P",)
    assert read.edition == 2


def test_a_plan_for_a_flight_that_is_not_on_file_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(StateError, match="no flight QH999/2025-05-12"):
        plans.save(conn, LoadPlan(flight_key="QH999/2025-05-12"))


def test_asking_for_a_plan_that_was_never_made(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no load plan for flight"):
        plans.get(conn, KEY)


def test_starting_a_plan_gives_an_empty_one(conn: sqlite3.Connection) -> None:
    started = plans.get_or_start(conn, KEY)
    assert started.empty
    assert started.edition == 1


def test_starting_a_plan_that_exists_gives_the_stored_one(conn: sqlite3.Connection) -> None:
    plans.save(conn, plan(pallet()))
    assert plans.get_or_start(conn, KEY).payload == 2000


def test_starting_a_plan_for_no_flight_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(StateError, match="no flight"):
        plans.get_or_start(conn, "QH999/2025-05-12")


def test_a_plan_can_be_thrown_away(conn: sqlite3.Connection) -> None:
    plans.save(conn, plan(pallet()))
    plans.remove(conn, KEY)
    assert not plans.exists(conn, KEY)
    assert plans.count(conn) == 0


def test_throwing_away_a_plan_that_is_not_there_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no load plan"):
        plans.remove(conn, KEY)


def test_the_flights_carrying_a_device_come_back(conn: sqlite3.Connection) -> None:
    plans.save(conn, plan(pallet()))
    assert plans.flights_carrying(conn, "pmc12345qh") == [KEY]
    assert plans.flights_carrying(conn, "PMC99999QH") == []


def test_removing_a_plan_takes_its_assignments_with_it(conn: sqlite3.Connection) -> None:
    plans.save(conn, plan(pallet()))
    plans.remove(conn, KEY)
    assert plans.flights_carrying(conn, "PMC12345QH") == []
