import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from holdtrim.errors import DataError, NotFoundError
from holdtrim.model.movement import Movement, movement
from holdtrim.store import movements
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def moved(
    day: date = date(2025, 5, 12),
    station: str = "BLL",
    code: str = "PMC12345QH",
    direction: str = "in",
    **changes: object,
) -> Movement:
    return movement(day=day, station=station, uld=code, direction=direction, **changes)  # type: ignore[arg-type]


def test_a_direction_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="not a direction"):
        moved(direction="sideways")


def test_a_state_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="not a state"):
        moved(state="soggy")


def test_an_arrival_adds_one_to_the_count() -> None:
    assert moved().inbound
    assert moved().effect == 1
    assert moved(direction="out").effect == -1


def test_a_movement_with_no_flight_was_by_road() -> None:
    assert not moved().on_a_flight
    assert "by road" in moved().describe()


def test_a_movement_on_a_flight_names_it() -> None:
    line = moved(flight_key="QH412/2025-05-12").describe()
    assert "QH412/2025-05-12" in line


def test_a_note_reaches_the_line() -> None:
    assert moved(note="corner damage").describe().endswith("corner damage")


def test_the_base_reads_off_the_code() -> None:
    assert moved().base == "PMC"


def test_a_movement_goes_in_the_log_and_comes_back(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved())
    assert movements.listing(conn) == [moved()]
    assert movements.count(conn) == 1


def test_one_device_history_comes_back_oldest_first(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved(day=date(2025, 5, 14), direction="out"))
    movements.record(conn, moved(day=date(2025, 5, 12)))
    assert [m.day.day for m in movements.for_uld(conn, "pmc12345qh")] == [12, 14]


def test_another_device_does_not_show(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved())
    assert movements.for_uld(conn, "PMC99999QH") == []


def test_a_station_log_narrows_by_day(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved(day=date(2025, 5, 10)))
    movements.record(conn, moved(day=date(2025, 5, 14), code="PMC12346QH"))
    found = movements.at_station(conn, "BLL", since=date(2025, 5, 12))
    assert [m.uld.serial for m in found] == ["12346"]


def test_everything_on_one_flight_comes_back(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved(flight_key="QH412/2025-05-12"))
    movements.record(conn, moved(code="PMC12346QH"))
    found = movements.for_flight(conn, "QH412/2025-05-12")
    assert [m.uld.serial for m in found] == ["12345"]


def test_a_flight_with_nothing_logged_comes_back_empty(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved())
    assert movements.for_flight(conn, "QH999/2025-05-12") == []


def test_the_balance_counts_arrivals_less_departures(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved(code="PMC12345QH"))
    movements.record(conn, moved(code="PMC12346QH"))
    movements.record(conn, moved(code="AKE10001QH"))
    movements.record(conn, moved(code="PMC12345QH", day=date(2025, 5, 14), direction="out"))
    assert movements.balance(conn, "BLL", date(2025, 5, 20)) == {"AKE": 1, "PMC": 1}


def test_the_balance_reads_as_at_a_day(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved())
    movements.record(conn, moved(day=date(2025, 5, 14), direction="out"))
    assert movements.balance(conn, "BLL", date(2025, 5, 13)) == {"PMC": 1}
    assert movements.balance(conn, "BLL", date(2025, 5, 20)) == {}


def test_the_last_movement_of_a_device_comes_back(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved())
    movements.record(conn, moved(day=date(2025, 5, 14), direction="out"))
    assert movements.last_seen(conn, "PMC12345QH").direction == "out"


def test_a_device_that_has_never_moved_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no movement has ever been recorded"):
        movements.last_seen(conn, "PMC12345QH")


def test_a_standing_device_says_when_it_arrived(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved())
    assert movements.standing_since(conn, "PMC12345QH") == date(2025, 5, 12)


def test_a_device_that_has_left_is_not_standing_anywhere(conn: sqlite3.Connection) -> None:
    movements.record(conn, moved())
    movements.record(conn, moved(day=date(2025, 5, 14), direction="out"))
    with pytest.raises(NotFoundError, match="left BLL on 2025-05-14"):
        movements.standing_since(conn, "PMC12345QH")
