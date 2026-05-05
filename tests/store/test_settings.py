import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from holdtrim.errors import DataError, NotFoundError
from holdtrim.store import settings
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def test_a_setting_nobody_defined_is_refused() -> None:
    with pytest.raises(NotFoundError, match="no setting called"):
        settings.known("weight.of.the.world")


def test_a_setting_reads_its_default_until_it_is_set(conn: sqlite3.Connection) -> None:
    assert settings.whole(conn, "lmc.tolerance") == 500
    assert settings.stored(conn, "lmc.tolerance") is None


def test_setting_one_changes_what_it_reads(conn: sqlite3.Connection) -> None:
    settings.put(conn, "lmc.tolerance", "300")
    assert settings.whole(conn, "lmc.tolerance") == 300
    assert settings.stored(conn, "lmc.tolerance") == "300"


def test_setting_one_twice_keeps_the_last_value(conn: sqlite3.Connection) -> None:
    settings.put(conn, "lmc.tolerance", "300")
    settings.put(conn, "lmc.tolerance", "400")
    assert settings.whole(conn, "lmc.tolerance") == 400
    assert settings.count(conn) == 1


def test_a_value_that_is_not_a_number_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(DataError, match="has to be a whole number"):
        settings.put(conn, "lmc.tolerance", "quite a lot")


def test_a_text_setting_takes_text(conn: sqlite3.Connection) -> None:
    settings.put(conn, "office.station", "BLL")
    assert settings.text(conn, "office.station") == "BLL"


def test_reading_a_text_setting_as_a_number_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(DataError, match="is text, not a whole number"):
        settings.whole(conn, "office.station")


def test_clearing_puts_it_back_to_the_default(conn: sqlite3.Connection) -> None:
    settings.put(conn, "lmc.tolerance", "300")
    settings.clear(conn, "lmc.tolerance")
    assert settings.whole(conn, "lmc.tolerance") == 500


def test_clearing_one_that_was_never_set_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="has never been set"):
        settings.clear(conn, "lmc.tolerance")


def test_the_listing_says_where_each_value_came_from(conn: sqlite3.Connection) -> None:
    settings.put(conn, "lmc.tolerance", "300")
    found = {setting.name: (value, was_set) for setting, value, was_set in settings.listing(conn)}
    assert found["lmc.tolerance"] == ("300", True)
    assert found["demurrage.free_days"] == ("5", False)


def test_a_setting_describes_itself() -> None:
    line = settings.known("lmc.tolerance").describe("500")
    assert line.startswith("lmc.tolerance 500 (")


def test_the_name_is_normalised(conn: sqlite3.Connection) -> None:
    settings.put(conn, "LMC.Tolerance", "300")
    assert settings.whole(conn, "lmc.tolerance") == 300
