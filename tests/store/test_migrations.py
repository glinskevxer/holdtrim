import sqlite3
from pathlib import Path

import pytest

from holdtrim.errors import BookError
from holdtrim.store import migrations
from holdtrim.store.migrations import (
    MIGRATIONS,
    Migration,
    ahead_of_this_build,
    applied,
    apply,
    check_order,
    current_version,
    pending,
)
from holdtrim.store.sqlite import opened, scalar, table_names


@pytest.fixture
def book(tmp_path: Path) -> Path:
    return tmp_path / "book.sqlite3"


def test_an_empty_book_is_at_version_zero(book: Path) -> None:
    with opened(book) as conn:
        assert current_version(conn) == 0
        assert applied(conn) == []


def test_everything_is_pending_on_an_empty_book(book: Path) -> None:
    with opened(book) as conn:
        assert len(pending(conn)) == len(MIGRATIONS)


def test_applying_runs_every_migration_once(book: Path) -> None:
    with opened(book) as conn:
        ran = apply(conn)
        assert [m.version for m in ran] == [m.version for m in MIGRATIONS]
        assert apply(conn) == []
        assert current_version(conn) == MIGRATIONS[-1].version


def test_the_station_table_exists_after_the_first_migration(book: Path) -> None:
    with opened(book) as conn:
        apply(conn)
        assert "station" in table_names(conn)


def test_the_applied_versions_are_recorded_by_name(book: Path) -> None:
    with opened(book) as conn:
        apply(conn)
        name = scalar(conn, "SELECT name FROM schema_migration WHERE version = 1")
        assert name == "stations"


def test_migrations_are_numbered_one_by_one() -> None:
    check_order()


def test_a_gap_in_the_numbering_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = (Migration(version=2, name="two", statements=()),)
    monkeypatch.setattr(migrations, "MIGRATIONS", broken)
    with pytest.raises(BookError, match="not numbered one by one"):
        check_order()


def test_two_migrations_sharing_a_name_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = (
        Migration(version=1, name="same", statements=()),
        Migration(version=2, name="same", statements=()),
    )
    monkeypatch.setattr(migrations, "MIGRATIONS", broken)
    with pytest.raises(BookError, match="share a name"):
        check_order()


def test_a_book_from_a_newer_build_is_seen(book: Path) -> None:
    with opened(book) as conn:
        apply(conn)
        assert ahead_of_this_build(conn) == 0
        conn.execute(
            "INSERT INTO schema_migration (version, name) VALUES (?, ?)",
            (MIGRATIONS[-1].version + 2, "from the future"),
        )
        assert ahead_of_this_build(conn) == 2


def test_a_failed_migration_leaves_nothing_behind(
    book: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = (
        Migration(
            version=1,
            name="half",
            statements=("CREATE TABLE good (a INTEGER)", "CREATE TABLE bad (a INTEGER"),
        ),
    )
    monkeypatch.setattr(migrations, "MIGRATIONS", broken)
    with opened(book) as conn:
        with pytest.raises(sqlite3.OperationalError, match="incomplete input"):
            apply(conn)
        assert "good" not in table_names(conn)
        assert applied(conn) == []
