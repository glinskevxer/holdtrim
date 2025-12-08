import csv
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from holdtrim.errors import BookError
from holdtrim.model.station import Station
from holdtrim.store import export, stations
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        stations.add(connection, Station(code="BLL", name="Billund", elevation_feet=247))
        stations.add(connection, Station(code="LGG", name="Liege", elevation_feet=659))
        yield connection


def test_the_schema_table_is_not_exported(conn: sqlite3.Connection) -> None:
    assert "schema_migration" not in export.exportable(conn)
    assert "station" in export.exportable(conn)


def test_the_columns_come_back_in_book_order(conn: sqlite3.Connection) -> None:
    assert export.columns(conn, "station")[:2] == ["code", "name"]


def test_a_table_that_is_not_there_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(BookError, match="no table called nowhere"):
        export.columns(conn, "nowhere")


def test_one_table_writes_out_with_a_header(conn: sqlite3.Connection, tmp_path: Path) -> None:
    written = export.table(conn, "station", tmp_path)
    assert written.written == 2
    with written.path.open(encoding="utf-8") as handle:
        read = list(csv.reader(handle))
    assert read[0][0] == "code"
    assert read[1][0] == "BLL"


def test_an_empty_table_still_writes_its_header(conn: sqlite3.Connection, tmp_path: Path) -> None:
    written = export.table(conn, "tail", tmp_path)
    assert written.written == 0
    assert written.path.read_text(encoding="utf-8").startswith("registration,")


def test_a_written_file_describes_itself(conn: sqlite3.Connection, tmp_path: Path) -> None:
    assert export.table(conn, "station", tmp_path).describe() == ("station 2 row(s) to station.csv")


def test_everything_writes_one_file_per_table(conn: sqlite3.Connection, tmp_path: Path) -> None:
    written = export.everything(conn, tmp_path / "out")
    names = sorted(entry.path.name for entry in written)
    assert "station.csv" in names
    assert "uld.csv" in names
    assert len(list((tmp_path / "out").glob("*.csv"))) == len(written)


def test_the_export_makes_the_directory(conn: sqlite3.Connection, tmp_path: Path) -> None:
    export.everything(conn, tmp_path / "deep" / "down")
    assert (tmp_path / "deep" / "down" / "station.csv").exists()


def test_exporting_over_a_file_is_refused(conn: sqlite3.Connection, tmp_path: Path) -> None:
    target = tmp_path / "not-a-directory"
    target.write_text("mine")
    with pytest.raises(BookError, match="not a directory"):
        export.everything(conn, target)


def test_the_total_counts_every_row(conn: sqlite3.Connection, tmp_path: Path) -> None:
    assert export.total(export.everything(conn, tmp_path / "out")) == 2
