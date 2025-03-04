from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim import __version__
from holdtrim.cli.common import exit_code_for, table
from holdtrim.cli.main import cli
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
