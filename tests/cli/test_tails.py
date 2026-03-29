from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from holdtrim.cli import tails
from holdtrim.cli.main import cli
from holdtrim.schedule.document import save_schedule
from tests.fleet.test_type_store import a_type


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return runner.invoke(cli, ["--book", str(book), *args])


@pytest.fixture
def fleet_book(runner: CliRunner, book: Path, tmp_path: Path) -> Path:
    schedule = save_schedule(a_type(), tmp_path / "at7f.json")
    run(runner, book, "init")
    run(runner, book, "fleet", "load", str(schedule))
    return book


def added(runner: CliRunner, book: Path, registration: str = "OY-JAF") -> Result:
    return run(
        runner,
        book,
        "tail",
        "add",
        registration,
        "AT7F",
        "--dow",
        "13640",
        "--doi",
        "46.2",
        "--weighed",
        "2024-06-18",
        "--serial",
        "0412",
    )


def test_an_aeroplane_goes_on_the_fleet(runner: CliRunner, fleet_book: Path) -> None:
    result = added(runner, fleet_book)
    assert "added OY-JAF AT7F DOW 13640 kg" in result.output


def test_the_fleet_lists_every_aeroplane(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    result = run(runner, fleet_book, "tail", "list")
    assert "OY-JAF" in result.output
    assert "in service" in result.output


def test_an_empty_fleet_says_so(runner: CliRunner, fleet_book: Path) -> None:
    assert "no aeroplanes on the fleet" in run(runner, fleet_book, "tail", "list").output


def test_the_list_narrows_to_one_type(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    result = run(runner, fleet_book, "tail", "list", "--type", "B734")
    assert "no aeroplanes on the fleet" in result.output


def test_an_aeroplane_shows_in_full(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    result = run(runner, fleet_book, "tail", "show", "oy-jaf")
    assert "weighing expires 2029-06-18" in result.output
    assert "serial 0412" in result.output


def test_the_days_of_weighing_left_read_as_at_a_day(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    result = run(runner, fleet_book, "tail", "show", "OY-JAF", "--on", "2029-06-08")
    assert "good for another 10 days" in result.output


def test_an_expired_weighing_says_how_long_ago(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    result = run(runner, fleet_book, "tail", "show", "OY-JAF", "--on", "2029-06-28")
    assert "expired 10 days ago" in result.output


def test_an_aeroplane_moves_out_of_service(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    run(runner, fleet_book, "tail", "status", "OY-JAF", "maintenance")
    assert "status maintenance" in run(runner, fleet_book, "tail", "show", "OY-JAF").output


def test_a_status_that_is_not_a_status_is_refused(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    result = run(runner, fleet_book, "tail", "status", "OY-JAF", "broken")
    assert result.exit_code != 0


def test_a_variation_moves_both_figures(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    run(runner, fleet_book, "tail", "vary", "OY-JAF", "--weight", "-120", "--index", "-0.8")
    result = run(runner, fleet_book, "tail", "show", "OY-JAF")
    assert "dry operating weight 13520 kg" in result.output
    assert "dry operating index 45.4" in result.output


def test_weighings_due_lists_the_ones_running_out(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    result = run(runner, fleet_book, "tail", "weighings", "--on", "2029-05-01", "--within", "90")
    assert "OY-JAF" in result.output
    assert "2029-06-18" in result.output


def test_nothing_due_says_so(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    result = run(runner, fleet_book, "tail", "weighings", "--on", "2025-01-01")
    assert "no weighings due within 90 days of 2025-01-01" in result.output


def test_an_aeroplane_can_come_off_the_fleet(runner: CliRunner, fleet_book: Path) -> None:
    added(runner, fleet_book)
    run(runner, fleet_book, "tail", "remove", "OY-JAF")
    assert "no aeroplanes on the fleet" in run(runner, fleet_book, "tail", "list").output


def test_the_group_is_registered_under_its_name() -> None:
    assert cli.commands["tail"] is tails.group
