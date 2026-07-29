import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.errors import BookError
from holdtrim.ids import AirWaybill
from holdtrim.model.consignment import Consignment
from holdtrim.model.movement import movement
from holdtrim.store import consignments, maintenance, movements
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def waybill(serial: int, ready: date) -> Consignment:
    return Consignment(
        awb=AirWaybill(prefix="125", serial=serial),
        origin="BLL",
        destination="LGG",
        pieces=4,
        gross_weight=400,
        volume=Decimal("1.200"),
        commodity="parts",
        ready_on=ready,
    )


def test_the_sizes_come_back_biggest_first(conn: sqlite3.Connection) -> None:
    for serial in (1234567, 2000004, 3000003):
        consignments.add(conn, waybill(serial, date(2025, 5, 12)))
    sizes = maintenance.sizes(conn)
    held = {size.table: size.rows for size in sizes}
    assert held["consignment"] == 3
    assert [size.rows for size in sizes] == sorted((size.rows for size in sizes), reverse=True)


def test_a_size_describes_itself(conn: sqlite3.Connection) -> None:
    assert maintenance.sizes(conn)[0].describe().endswith("row(s)")


def test_the_file_size_reads_off_disk(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    with opened(path) as connection:
        apply(connection)
    assert maintenance.file_size(path) > 0


def test_a_book_that_is_not_there_has_no_size(tmp_path: Path) -> None:
    with pytest.raises(BookError, match="no book at"):
        maintenance.file_size(tmp_path / "missing.sqlite3")


def test_analysing_and_vacuuming_leave_the_rows_alone(conn: sqlite3.Connection) -> None:
    consignments.add(conn, waybill(1234567, date(2025, 5, 12)))
    maintenance.analyse(conn)
    maintenance.vacuum(conn)
    assert consignments.count(conn) == 1


def test_the_indexes_come_back_in_name_order(conn: sqlite3.Connection) -> None:
    names = maintenance.index_names(conn)
    assert "station_by_name" in names
    assert names == sorted(names)


def test_the_reports_have_the_indexes_they_read_through(conn: sqlite3.Connection) -> None:
    names = maintenance.index_names(conn)
    assert "sector_by_origin" in names
    assert "uld_movement_by_flight" in names


def test_a_query_plan_reads_back(conn: sqlite3.Connection) -> None:
    plan = maintenance.query_plan(conn, "SELECT code FROM station WHERE code = 'BLL'")
    assert plan
    assert any("station" in line for line in plan)


def test_every_watched_query_has_a_plan(conn: sqlite3.Connection) -> None:
    for statement in maintenance.WATCHED_QUERIES.values():
        assert maintenance.query_plan(conn, statement)


def test_the_watched_queries_use_their_indexes(conn: sqlite3.Connection) -> None:
    maintenance.analyse(conn)
    assert maintenance.scans(conn) == {}


def test_a_query_with_no_index_is_reported_as_a_scan(conn: sqlite3.Connection) -> None:
    plan = maintenance.query_plan(conn, "SELECT name FROM station WHERE elevation_feet > 100")
    assert any(line.startswith("SCAN") for line in plan)


def test_a_dry_run_says_what_would_go_and_takes_nothing(conn: sqlite3.Connection) -> None:
    consignments.add(conn, waybill(1234567, date(2024, 1, 2)))
    would = maintenance.would_prune(conn, date(2025, 1, 1))
    assert would[0].table == "consignment"
    assert consignments.count(conn) == 1


def test_pruning_takes_the_old_rows_out(conn: sqlite3.Connection) -> None:
    consignments.add(conn, waybill(1234567, date(2024, 1, 2)))
    consignments.add(conn, waybill(2000004, date(2025, 5, 12)))
    taken = maintenance.prune(conn, date(2025, 1, 1))
    assert taken[0].rows == 1
    assert consignments.count(conn) == 1


def test_pruning_takes_the_movement_log_with_it(conn: sqlite3.Connection) -> None:
    movements.record(
        conn, movement(day=date(2024, 1, 2), station="BLL", uld="PMC12345QH", direction="in")
    )
    maintenance.prune(conn, date(2025, 1, 1))
    assert movements.count(conn) == 0


def test_a_book_with_nothing_old_prunes_nothing(conn: sqlite3.Connection) -> None:
    consignments.add(conn, waybill(1234567, date(2025, 5, 12)))
    assert maintenance.prune(conn, date(2025, 1, 1)) == ()


def test_every_dated_table_has_a_prune_statement() -> None:
    assert set(maintenance.PRUNE_STATEMENTS) == set(maintenance.DATED_TABLES)


def test_the_flights_are_pruned_after_what_points_at_them() -> None:
    order = list(maintenance.PRUNE_STATEMENTS)
    assert order[-1] == "sector"


def test_a_pruned_entry_describes_itself(conn: sqlite3.Connection) -> None:
    consignments.add(conn, waybill(1234567, date(2024, 1, 2)))
    entry = maintenance.would_prune(conn, date(2025, 1, 1))[0]
    assert entry.describe() == "consignment 1 row(s) before 2025-01-01"


def test_a_table_that_is_not_in_the_book_is_not_pruned(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE loadsheet")
    assert maintenance.would_prune(conn, date(2025, 1, 1)) == ()


def test_the_sizes_leave_out_nothing_that_is_there(conn: sqlite3.Connection) -> None:
    tables = {size.table for size in maintenance.sizes(conn)}
    assert "setting" in tables
