import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from holdtrim.errors import NotFoundError
from holdtrim.store.records import counted, dropped, held
from holdtrim.store.sqlite import opened

EXISTS = "SELECT count(*) FROM thing WHERE code = ?"
DELETE = "DELETE FROM thing WHERE code = ?"
COUNT = "SELECT count(*) FROM thing"


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        connection.execute("CREATE TABLE thing (code TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO thing VALUES ('one')")
        yield connection


def test_a_row_that_is_there_is_held(conn: sqlite3.Connection) -> None:
    assert held(conn, EXISTS, "one")


def test_a_row_that_is_not_there_is_not_held(conn: sqlite3.Connection) -> None:
    assert not held(conn, EXISTS, "two")


def test_the_rows_are_counted(conn: sqlite3.Connection) -> None:
    assert counted(conn, COUNT) == 1


def test_dropping_takes_the_row_out(conn: sqlite3.Connection) -> None:
    dropped(
        conn,
        exists_statement=EXISTS,
        delete_statement=DELETE,
        key="one",
        missing="no thing called one",
    )
    assert counted(conn, COUNT) == 0


def test_dropping_something_that_is_not_there_says_so(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no thing called two"):
        dropped(
            conn,
            exists_statement=EXISTS,
            delete_statement=DELETE,
            key="two",
            missing="no thing called two",
        )


def test_a_failed_drop_leaves_the_rest_alone(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError):
        dropped(
            conn,
            exists_statement=EXISTS,
            delete_statement=DELETE,
            key="two",
            missing="no thing called two",
        )
    assert counted(conn, COUNT) == 1
