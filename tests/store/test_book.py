from pathlib import Path

import pytest

from holdtrim.errors import BookError
from holdtrim.model.station import Station
from holdtrim.store import stations
from holdtrim.store.book import Book, copy_book, initialise, open_book
from holdtrim.store.migrations import MIGRATIONS
from holdtrim.store.sqlite import connect


def test_initialising_creates_a_book_at_the_current_schema(tmp_path: Path) -> None:
    path = initialise(tmp_path / "book.sqlite3")
    assert path.exists()
    with open_book(path) as book:
        assert book.version == MIGRATIONS[-1].version


def test_opening_a_book_that_is_not_there_says_to_run_init(tmp_path: Path) -> None:
    with pytest.raises(BookError, match="run init first"), open_book(tmp_path / "missing.sqlite3"):
        pass


def test_opening_with_create_makes_one(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    with open_book(path, create=True) as book:
        assert book.counts() == {
            "station": 0,
            "aircraft_type": 0,
            "tail": 0,
            "consignment": 0,
        }
    assert path.exists()


def test_counts_follow_the_rows(tmp_path: Path) -> None:
    with open_book(tmp_path / "book.sqlite3", create=True) as book:
        stations.add(book.connection, Station(code="BLL", name="Billund", elevation_feet=247))
        assert book.counts()["station"] == 1


def test_a_sound_book_verifies_clean(tmp_path: Path) -> None:
    with open_book(tmp_path / "book.sqlite3", create=True) as book:
        assert book.verify() == []


def test_a_book_behind_the_schema_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    connection = connect(path)
    connection.execute("CREATE TABLE schema_migration (version INTEGER PRIMARY KEY, name TEXT)")
    connection.close()
    with pytest.raises(BookError, match="run init"), open_book(path):
        pass


def test_a_book_from_a_newer_build_is_refused(tmp_path: Path) -> None:
    path = initialise(tmp_path / "book.sqlite3")
    connection = connect(path)
    connection.execute(
        "INSERT INTO schema_migration (version, name) VALUES (?, ?)",
        (MIGRATIONS[-1].version + 1, "later"),
    )
    connection.close()
    with pytest.raises(BookError, match="newer holdtrim"), open_book(path):
        pass


def test_a_book_missing_a_migration_says_so_in_verify(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    connection = connect(path)
    connection.execute("CREATE TABLE schema_migration (version INTEGER PRIMARY KEY, name TEXT)")
    book = Book(path=path, connection=connection)
    problems = book.verify()
    book.close()
    assert any("have not been applied" in problem for problem in problems)


def test_a_backup_is_a_readable_book(tmp_path: Path) -> None:
    with open_book(tmp_path / "book.sqlite3", create=True) as book:
        stations.add(book.connection, Station(code="BLL", name="Billund", elevation_feet=247))
        book.backup(tmp_path / "copy.sqlite3")
    with open_book(tmp_path / "copy.sqlite3") as copied:
        assert stations.count(copied.connection) == 1


def test_a_backup_will_not_write_over_a_file(tmp_path: Path) -> None:
    target = tmp_path / "copy.sqlite3"
    target.write_text("mine")
    with (
        open_book(tmp_path / "book.sqlite3", create=True) as book,
        pytest.raises(BookError, match="not writing over it"),
    ):
        book.backup(target)


def test_copying_a_closed_book_gives_the_same_rows(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    with open_book(path, create=True) as book:
        stations.add(book.connection, Station(code="BLL", name="Billund", elevation_feet=247))
    copy_book(path, tmp_path / "away.sqlite3")
    with open_book(tmp_path / "away.sqlite3") as copied:
        assert stations.count(copied.connection) == 1


def test_copying_from_nowhere_is_refused(tmp_path: Path) -> None:
    with pytest.raises(BookError, match="no book at"):
        copy_book(tmp_path / "nope.sqlite3", tmp_path / "away.sqlite3")


def test_copying_over_a_file_is_refused(tmp_path: Path) -> None:
    path = initialise(tmp_path / "book.sqlite3")
    target = tmp_path / "away.sqlite3"
    target.write_text("mine")
    with pytest.raises(BookError, match="not writing over it"):
        copy_book(path, target)
