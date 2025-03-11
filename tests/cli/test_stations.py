from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim.cli.main import cli


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return runner.invoke(cli, ["--book", str(book), *args])


def prepared(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    run(runner, book, "station", "add", "BLL", "Billund", "--elevation", "247")


def test_a_station_can_be_added_and_listed(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    result = run(runner, book, "station", "list")
    assert "BLL" in result.output
    assert "Billund" in result.output


def test_an_empty_register_says_so(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "station", "list")
    assert "no stations in the register" in result.output


def test_a_station_with_no_agent_lists_as_self_handled(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    assert "self handled" in run(runner, book, "station", "list").output


def test_a_station_shows_in_full(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    result = run(runner, book, "station", "show", "bll")
    assert "elevation 247 ft" in result.output
    assert "free storage 2 days" in result.output


def test_adding_the_same_code_twice_exits_four(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    result = run(runner, book, "station", "add", "BLL", "Billund", "--elevation", "247")
    assert result.exception is not None


def test_a_station_can_be_changed(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    run(runner, book, "station", "set", "BLL", "--agent", "BLL Cargo", "--free-days", "5")
    result = run(runner, book, "station", "show", "BLL")
    assert "agent BLL Cargo" in result.output
    assert "free storage 5 days" in result.output


def test_changing_nothing_leaves_it_alone(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    run(runner, book, "station", "set", "BLL")
    assert "Billund" in run(runner, book, "station", "show", "BLL").output


def test_a_station_can_be_removed(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    run(runner, book, "station", "remove", "BLL")
    assert "no stations in the register" in run(runner, book, "station", "list").output


def test_showing_a_station_that_is_not_there_raises(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "station", "show", "CDG")
    assert result.exception is not None
