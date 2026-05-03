import sqlite3
import sys
from pathlib import Path

import click
import pytest
from click.testing import CliRunner, Result

from holdtrim import __version__
from holdtrim.cli.common import exit_code_for, table
from holdtrim.cli.main import cli
from holdtrim.cli.main import run as run_entry_point
from holdtrim.errors import (
    BookError,
    DataError,
    DuplicateError,
    HoldtrimError,
    LimitError,
    NotFoundError,
)


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return runner.invoke(cli, ["--book", str(book), *args])


def test_init_creates_the_book(runner: CliRunner, book: Path) -> None:
    result = run(runner, book, "init")
    assert result.exit_code == 0
    assert "created" in result.output
    assert book.exists()


def test_init_again_brings_it_up_to_date(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "init")
    assert "brought up to date" in result.output


def test_about_names_the_build_and_the_book(runner: CliRunner, book: Path) -> None:
    result = run(runner, book, "about")
    assert __version__ in result.output
    assert str(book) in result.output


def test_the_version_option_prints_the_version(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert __version__ in result.output


def test_counts_lists_the_empty_tables(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "book", "counts")
    assert "station 0" in result.output
    assert "tail 0" in result.output
    assert "consignment 0" in result.output


def test_verify_says_a_fresh_book_is_sound(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "book", "verify")
    assert result.exit_code == 0
    assert "sound" in result.output


def test_backup_writes_a_second_file(runner: CliRunner, book: Path, tmp_path: Path) -> None:
    run(runner, book, "init")
    away = tmp_path / "away.sqlite3"
    result = run(runner, book, "book", "backup", str(away))
    assert result.exit_code == 0
    assert away.exists()


def test_working_on_a_book_that_is_not_there_is_refused(runner: CliRunner, book: Path) -> None:
    result = run(runner, book, "book", "counts")
    assert isinstance(result.exception, BookError)


def test_the_exit_code_map_is_most_specific_first() -> None:
    assert exit_code_for(DataError("no")) == 2
    assert exit_code_for(NotFoundError("no")) == 3
    assert exit_code_for(DuplicateError("no")) == 4
    assert exit_code_for(BookError("no")) == 7


def test_a_subclass_takes_the_code_of_its_parent() -> None:
    assert exit_code_for(LimitError("over", limit=1, actual=2)) == 6


def test_an_error_with_no_code_of_its_own_falls_back() -> None:
    assert exit_code_for(HoldtrimError("something else")) == 1


def test_a_table_lines_its_columns_up() -> None:
    printed = table(["code", "name"], [["BLL", "Billund"], ["AAR", "Aarhus"]])
    assert printed.splitlines()[0] == "code  name"
    assert printed.splitlines()[2] == "BLL   Billund"


def test_a_table_with_no_rows_is_empty() -> None:
    assert table(["code"], []) == ""


def test_the_entry_point_turns_a_refusal_into_an_exit_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["holdtrim", "--book", str(tmp_path / "missing.sqlite3"), "book", "counts"]
    )
    with pytest.raises(SystemExit) as raised:
        run_entry_point()
    assert raised.value.code == 7


def test_the_entry_point_reports_a_bad_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["holdtrim", "nonsense"])
    with pytest.raises(SystemExit) as raised:
        run_entry_point()
    assert raised.value.code != 0


def test_the_entry_point_exits_one_thirty_when_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    def abort() -> None:
        raise click.Abort

    monkeypatch.setattr(cli, "main", lambda **_kwargs: abort())
    with pytest.raises(SystemExit) as raised:
        run_entry_point()
    assert raised.value.code == 130


def test_a_book_with_a_dangling_reference_will_not_verify(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    connection = sqlite3.connect(book)
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("INSERT INTO load_plan (flight_key, edition) VALUES ('QH999/2025-05-12', 1)")
    connection.commit()
    connection.close()
    result = run(runner, book, "book", "verify")
    assert result.exit_code == 7
    assert "problem:" in result.output


def test_the_sizes_list_the_tables(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "book", "sizes")
    assert "station 0 row(s)" in result.output
    assert "bytes on disk" in result.output


def test_the_indexes_list_by_name(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    assert "station_by_name" in run(runner, book, "book", "indexes").output


def test_tidying_leaves_the_book_sound(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    assert "tidied" in run(runner, book, "book", "tidy").output
    assert "sound" in run(runner, book, "book", "verify").output


def test_a_book_with_nothing_old_prunes_nothing(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "book", "prune", "--before", "2020-01-01")
    assert "nothing in the book is older" in result.output
