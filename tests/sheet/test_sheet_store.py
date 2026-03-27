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
from holdtrim.store import fleet, flights, sheets
from holdtrim.store.migrations import apply
from holdtrim.store.sheets import Issued, from_sheet
from holdtrim.store.sqlite import opened
from tests.fleet.test_type_store import a_type
from tests.sheet.test_loadsheet import KEY, sheet

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
        flights.add(
            connection,
            Sector(
                designator=Flight(carrier="QH", number=412),
                day=DAY,
                registration="OY-JAF",
                origin="BLL",
                destination="LGG",
                taxi_fuel=90,
                trip_fuel=1450,
                takeoff_fuel=2600,
            ),
        )
        yield connection


def issued(edition: int = 1) -> Issued:
    return from_sheet(sheet(edition=edition), DAY)


def test_the_figures_come_off_the_loadsheet() -> None:
    taken = issued()
    assert taken.flight_key == KEY
    assert taken.payload == 2300
    assert taken.zero_fuel_weight == 15940
    assert taken.trim_setting == sheet().trim_setting


def test_an_edition_goes_on_the_record_and_comes_back(conn: sqlite3.Connection) -> None:
    sheets.record(conn, issued())
    assert sheets.held(conn, KEY, 1) == issued()


def test_an_edition_that_was_never_issued_comes_back_as_nothing(
    conn: sqlite3.Connection,
) -> None:
    assert sheets.held(conn, KEY, 4) is None


def test_the_same_edition_twice_is_refused(conn: sqlite3.Connection) -> None:
    sheets.record(conn, issued())
    with pytest.raises(DuplicateError, match="has already been issued"):
        sheets.record(conn, issued())


def test_a_loadsheet_for_a_flight_that_is_not_on_file(conn: sqlite3.Connection) -> None:
    taken = from_sheet(sheet(), DAY)
    other = Issued(**{**taken.__dict__, "flight_key": "QH999/2025-05-12"})
    with pytest.raises(StateError, match="no flight QH999"):
        sheets.record(conn, other)


def test_the_editions_come_back_first_to_last(conn: sqlite3.Connection) -> None:
    sheets.record(conn, issued(1))
    sheets.record(conn, issued(2))
    assert [entry.edition for entry in sheets.editions(conn, KEY)] == [1, 2]
    assert sheets.count(conn) == 2


def test_the_latest_edition_is_the_one_that_stands(conn: sqlite3.Connection) -> None:
    sheets.record(conn, issued(1))
    sheets.record(conn, issued(2))
    assert sheets.latest(conn, KEY).edition == 2


def test_a_flight_with_no_loadsheet_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no loadsheet has been issued"):
        sheets.latest(conn, KEY)


def test_the_next_edition_follows_what_is_there(conn: sqlite3.Connection) -> None:
    assert sheets.next_edition(conn, KEY) == 1
    sheets.record(conn, issued())
    assert sheets.next_edition(conn, KEY) == 2


def test_everything_issued_on_a_day_comes_back(conn: sqlite3.Connection) -> None:
    sheets.record(conn, issued())
    assert [entry.flight_key for entry in sheets.issued_on(conn, DAY)] == [KEY]
    assert sheets.issued_on(conn, date(2025, 5, 13)) == []


def test_an_issued_edition_describes_itself(conn: sqlite3.Connection) -> None:
    line = issued().describe()
    assert "edition 1 issued 2025-05-12 by K Ravn" in line
    assert "ZFW 15940" in line
