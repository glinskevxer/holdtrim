import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.errors import DuplicateError, NotFoundError, StateError
from holdtrim.model.tail import Tail
from holdtrim.store import fleet
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened
from tests.fleet.test_type_store import a_type


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        fleet.add_type(connection, a_type())
        yield connection


def tail(registration: str = "OY-JAF", **changes: object) -> Tail:
    fields: dict[str, object] = {
        "registration": registration,
        "type_code": "AT7F",
        "dry_operating_weight": 13640,
        "dry_operating_index": Decimal("46.2"),
        "weighed_on": date(2024, 6, 18),
        "serial_number": "0412",
    }
    fields.update(changes)
    return Tail(**fields)  # type: ignore[arg-type]


def test_an_aeroplane_goes_on_and_comes_back(conn: sqlite3.Connection) -> None:
    fleet.add_tail(conn, tail())
    assert fleet.get_tail(conn, "OY-JAF") == tail()


def test_the_index_comes_back_as_the_decimal_it_went_in_as(conn: sqlite3.Connection) -> None:
    fleet.add_tail(conn, tail(dry_operating_index=Decimal("-3.4")))
    assert fleet.get_tail(conn, "OY-JAF").dry_operating_index == Decimal("-3.4")


def test_the_weighing_date_survives_the_round_trip(conn: sqlite3.Connection) -> None:
    fleet.add_tail(conn, tail())
    assert fleet.get_tail(conn, "OY-JAF").weighed_on == date(2024, 6, 18)


def test_the_same_registration_twice_is_refused(conn: sqlite3.Connection) -> None:
    fleet.add_tail(conn, tail())
    with pytest.raises(DuplicateError, match="already on the fleet"):
        fleet.add_tail(conn, tail())


def test_an_aeroplane_of_an_unregistered_type_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(StateError, match="not in the fleet register yet"):
        fleet.add_tail(conn, tail(type_code="B734"))


def test_asking_for_an_aeroplane_that_is_not_on_the_fleet(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no aeroplane OY-JAG"):
        fleet.get_tail(conn, "OY-JAG")


def test_aeroplanes_list_in_registration_order(conn: sqlite3.Connection) -> None:
    fleet.add_tail(conn, tail("OY-JAG"))
    fleet.add_tail(conn, tail("OY-JAF"))
    assert [t.registration for t in fleet.list_tails(conn)] == ["OY-JAF", "OY-JAG"]
    assert fleet.count_tails(conn) == 2


def test_the_aeroplanes_of_one_type_come_back(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type("A306"))
    fleet.add_tail(conn, tail("OY-JAF"))
    fleet.add_tail(conn, tail("OY-SRR", type_code="A306"))
    assert [t.registration for t in fleet.tails_of_type(conn, "at7f")] == ["OY-JAF"]


def test_saving_overwrites_the_row(conn: sqlite3.Connection) -> None:
    fleet.add_tail(conn, tail())
    fleet.save_tail(conn, tail().with_variation(-120, Decimal("-0.8")))
    assert fleet.get_tail(conn, "OY-JAF").dry_operating_weight == 13520


def test_saving_an_aeroplane_that_was_never_added_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no aeroplane OY-JAG"):
        fleet.save_tail(conn, tail("OY-JAG"))


def test_removing_takes_it_off(conn: sqlite3.Connection) -> None:
    fleet.add_tail(conn, tail())
    fleet.remove_tail(conn, "OY-JAF")
    assert not fleet.tail_exists(conn, "OY-JAF")


def test_removing_one_that_is_not_there_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no aeroplane OY-JAG"):
        fleet.remove_tail(conn, "OY-JAG")


def test_weighings_coming_due_come_back_soonest_first(conn: sqlite3.Connection) -> None:
    fleet.add_tail(conn, tail("OY-JAF", weighed_on=date(2024, 6, 18)))
    fleet.add_tail(conn, tail("OY-JAG", weighed_on=date(2024, 1, 10)))
    fleet.add_tail(conn, tail("OY-JAH", weighed_on=date(2026, 1, 10)))
    due = fleet.weighings_due(conn, date(2029, 3, 1), within_days=120)
    assert [t.registration for t in due] == ["OY-JAG", "OY-JAF"]


def test_nothing_is_due_when_every_weighing_is_fresh(conn: sqlite3.Connection) -> None:
    fleet.add_tail(conn, tail(weighed_on=date(2026, 1, 10)))
    assert fleet.weighings_due(conn, date(2026, 3, 1)) == []
