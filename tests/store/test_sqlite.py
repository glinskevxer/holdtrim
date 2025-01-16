import sqlite3
from pathlib import Path

import pytest

from holdtrim.errors import BookError
from holdtrim.store.sqlite import (
    broken_references,
    connect,
    integrity,
    one,
    opened,
    rows,
    scalar,
    scalar_int,
    table_names,
    transaction,
)


@pytest.fixture
def book(tmp_path: Path) -> Path:
    return tmp_path / "book.sqlite3"


def test_the_connection_hands_back_rows_by_name(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE station (code TEXT PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO station VALUES ('BLL', 'Billund')")
        row = one(conn, "SELECT * FROM station WHERE code = ?", ("BLL",))
        assert row is not None
        assert row["name"] == "Billund"


def test_foreign_keys_are_on(book: Path) -> None:
    with opened(book) as conn:
        assert scalar(conn, "PRAGMA foreign_keys") == 1


def test_the_context_manager_closes_the_connection(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE t (a INTEGER)")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_a_missing_row_comes_back_as_nothing(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE t (a INTEGER)")
        assert one(conn, "SELECT * FROM t") is None


def test_every_row_of_a_query_reads_out(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE t (a INTEGER)")
        conn.executemany("INSERT INTO t VALUES (?)", [(1,), (2,), (3,)])
        assert [row["a"] for row in rows(conn, "SELECT a FROM t ORDER BY a")] == [1, 2, 3]


def test_a_scalar_with_no_row_is_a_book_error(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE t (a INTEGER)")
        with pytest.raises(BookError, match="no row came back"):
            scalar(conn, "SELECT a FROM t")


def test_a_transaction_commits_on_the_way_out(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE t (a INTEGER)")
        with transaction(conn):
            conn.execute("INSERT INTO t VALUES (1)")
        assert scalar(conn, "SELECT count(*) FROM t") == 1


def _insert_then_fail(conn: sqlite3.Connection) -> None:
    with transaction(conn):
        conn.execute("INSERT INTO t VALUES (1)")
        raise RuntimeError("changed my mind")


def test_a_transaction_rolls_back_when_the_body_raises(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE t (a INTEGER)")
        with pytest.raises(RuntimeError, match="changed my mind"):
            _insert_then_fail(conn)
        assert scalar(conn, "SELECT count(*) FROM t") == 0


def test_table_names_leave_out_sqlite_own(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE zulu (a INTEGER PRIMARY KEY AUTOINCREMENT)")
        conn.execute("CREATE TABLE alpha (a INTEGER)")
        assert table_names(conn) == ["alpha", "zulu"]


def test_a_healthy_file_reports_nothing_wrong(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE t (a INTEGER)")
        assert integrity(conn) == []


def test_a_dangling_reference_is_reported(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE child (id INTEGER, parent INTEGER REFERENCES parent(id))")
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("INSERT INTO child VALUES (1, 99)")
        conn.execute("PRAGMA foreign_keys = ON")
        assert broken_references(conn) == ["child row 1 references missing parent"]


def test_a_book_with_no_dangling_references_reports_none(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        assert broken_references(conn) == []


def test_a_count_reads_back_as_a_whole_number(book: Path) -> None:
    with opened(book) as conn:
        conn.execute("CREATE TABLE t (a INTEGER)")
        assert scalar_int(conn, "SELECT count(*) FROM t") == 0
        assert scalar_int(conn, "SELECT max(a) FROM t") == 0


def test_a_count_that_is_not_a_number_is_a_book_error(book: Path) -> None:
    with opened(book) as conn, pytest.raises(BookError, match="expected a whole number"):
        scalar_int(conn, "SELECT 'plenty'")


def test_connect_is_available_for_callers_that_close_themselves(book: Path) -> None:
    conn = connect(book)
    try:
        assert scalar(conn, "SELECT 1") == 1
    finally:
        conn.close()
