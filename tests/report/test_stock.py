import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from holdtrim.model.movement import movement
from holdtrim.model.uld import uld
from holdtrim.report import stock
from holdtrim.report.stock import Standing, StockLine
from holdtrim.store import movements, ulds
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def add(
    conn: sqlite3.Connection, code: str, station: str = "BLL", condition: str = "serviceable"
) -> None:
    ulds.add(
        conn,
        uld(code=code, tare=110, max_gross=4626, at_station=station, condition=condition),
    )


def arrive(conn: sqlite3.Connection, code: str, day: date, station: str = "BLL") -> None:
    movements.record(conn, movement(day=day, station=station, uld=code, direction="in"))


def test_a_stock_line_counts_what_cannot_be_loaded() -> None:
    line = StockLine(base="PMC", held=4, serviceable=3, damaged=1)
    assert line.unusable == 1
    assert "4 held, 3 serviceable, 1 damaged" in line.describe()


def test_the_register_view_counts_by_base(conn: sqlite3.Connection) -> None:
    add(conn, "PMC12345QH")
    add(conn, "PMC12346QH", condition="damaged")
    add(conn, "AKE10001QH")
    lines = stock.at(conn, "BLL")
    assert [line.base for line in lines] == ["AKE", "PMC"]
    assert lines[1].held == 2
    assert lines[1].damaged == 1


def test_a_station_holding_nothing_has_no_lines(conn: sqlite3.Connection) -> None:
    assert stock.at(conn, "CDG") == ()


def test_the_register_and_the_log_agreeing_reports_nothing(conn: sqlite3.Connection) -> None:
    add(conn, "PMC12345QH")
    arrive(conn, "PMC12345QH", date(2025, 5, 1))
    assert stock.disagreements(conn, "BLL", date(2025, 5, 12)) == ()


def test_a_device_in_the_register_and_not_the_log_is_reported(
    conn: sqlite3.Connection,
) -> None:
    add(conn, "PMC12345QH")
    assert stock.disagreements(conn, "BLL", date(2025, 5, 12)) == (("PMC", 1, 0),)


def test_a_device_in_the_log_and_not_the_register_is_reported(
    conn: sqlite3.Connection,
) -> None:
    arrive(conn, "PMC12345QH", date(2025, 5, 1))
    assert stock.disagreements(conn, "BLL", date(2025, 5, 12)) == (("PMC", 0, 1),)


def test_a_standing_device_counts_its_days(conn: sqlite3.Connection) -> None:
    add(conn, "PMC12345QH")
    arrive(conn, "PMC12345QH", date(2025, 5, 1))
    found = stock.standing(conn, "BLL", date(2025, 5, 12))
    assert found[0].days == 11
    assert found[0].chargeable_days == 6


def test_a_device_inside_its_free_days_owes_nothing(conn: sqlite3.Connection) -> None:
    add(conn, "PMC12345QH")
    arrive(conn, "PMC12345QH", date(2025, 5, 10))
    found = stock.standing(conn, "BLL", date(2025, 5, 12))
    assert not found[0].chargeable
    assert found[0].charge == 0


def test_the_longest_standing_device_comes_first(conn: sqlite3.Connection) -> None:
    add(conn, "PMC12345QH")
    add(conn, "PMC12346QH")
    arrive(conn, "PMC12345QH", date(2025, 5, 10))
    arrive(conn, "PMC12346QH", date(2025, 5, 1))
    found = stock.standing(conn, "BLL", date(2025, 5, 12))
    assert [entry.uld for entry in found] == ["PMC12346QH", "PMC12345QH"]


def test_a_device_with_no_arrival_logged_is_left_out(conn: sqlite3.Connection) -> None:
    add(conn, "PMC12345QH")
    assert stock.standing(conn, "BLL", date(2025, 5, 12)) == ()


def test_the_charge_follows_the_rate(conn: sqlite3.Connection) -> None:
    add(conn, "PMC12345QH")
    arrive(conn, "PMC12345QH", date(2025, 5, 1))
    found = stock.standing(conn, "BLL", date(2025, 5, 12), free_days=5, daily_rate=10)
    assert found[0].charge == 60


def test_what_a_station_owes_adds_up(conn: sqlite3.Connection) -> None:
    add(conn, "PMC12345QH")
    add(conn, "PMC12346QH")
    arrive(conn, "PMC12345QH", date(2025, 5, 1))
    arrive(conn, "PMC12346QH", date(2025, 5, 2))
    assert stock.owing(conn, "BLL", date(2025, 5, 12)) == 6 * 6 + 5 * 6


def test_a_station_owing_nothing_owes_nothing(conn: sqlite3.Connection) -> None:
    assert stock.owing(conn, "CDG", date(2025, 5, 12)) == 0


def test_a_standing_entry_describes_itself() -> None:
    entry = Standing(
        uld="PMC12345QH",
        base="PMC",
        since=date(2025, 5, 1),
        days=11,
        free_days=5,
        daily_rate=6,
    )
    assert entry.describe().startswith("PMC12345QH standing since 2025-05-01")
