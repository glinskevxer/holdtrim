import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from holdtrim.errors import DuplicateError, NotFoundError
from holdtrim.model.station import Station
from holdtrim.store import stations
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def billund() -> Station:
    return Station(code="BLL", name="Billund", elevation_feet=247, handling_agent="BLL Cargo")


def test_a_station_goes_in_and_comes_back(conn: sqlite3.Connection) -> None:
    stations.add(conn, billund())
    assert stations.get(conn, "BLL") == billund()


def test_a_lower_case_code_finds_the_same_row(conn: sqlite3.Connection) -> None:
    stations.add(conn, billund())
    assert stations.get(conn, "bll").name == "Billund"


def test_adding_the_same_code_twice_is_refused(conn: sqlite3.Connection) -> None:
    stations.add(conn, billund())
    with pytest.raises(DuplicateError, match="already in the register"):
        stations.add(conn, billund())


def test_asking_for_a_station_that_is_not_there(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no station CDG"):
        stations.get(conn, "CDG")


def test_the_listing_comes_back_in_code_order(conn: sqlite3.Connection) -> None:
    stations.add(conn, billund())
    stations.add(conn, Station(code="AAR", name="Aarhus", elevation_feet=82))
    assert [station.code for station in stations.listing(conn)] == ["AAR", "BLL"]


def test_an_empty_register_lists_nothing(conn: sqlite3.Connection) -> None:
    assert stations.listing(conn) == []
    assert stations.count(conn) == 0


def test_saving_overwrites_the_row(conn: sqlite3.Connection) -> None:
    stations.add(conn, billund())
    changed = Station(
        code="BLL", name="Billund", elevation_feet=247, handling_agent="", free_storage_days=4
    )
    stations.save(conn, changed)
    assert stations.get(conn, "BLL").free_storage_days == 4
    assert stations.get(conn, "BLL").self_handled


def test_saving_a_station_that_was_never_added_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no station CDG"):
        stations.save(conn, Station(code="CDG", name="Paris", elevation_feet=392))


def test_removing_takes_it_out(conn: sqlite3.Connection) -> None:
    stations.add(conn, billund())
    stations.remove(conn, "BLL")
    assert not stations.exists(conn, "BLL")
    assert stations.count(conn) == 0


def test_removing_something_that_is_not_there_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no station CDG"):
        stations.remove(conn, "CDG")


def test_exists_answers_without_raising(conn: sqlite3.Connection) -> None:
    assert not stations.exists(conn, "BLL")
    stations.add(conn, billund())
    assert stations.exists(conn, "BLL")
