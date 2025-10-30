from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from holdtrim.cli import flights
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
    run(
        runner,
        book,
        "tail",
        "add",
        "OY-JAF",
        "AT7F",
        "--dow",
        "13640",
        "--doi",
        "46.2",
        "--weighed",
        "2024-06-18",
    )
    return book


def filed(runner: CliRunner, book: Path, designator: str = "QH412", **extra: str) -> Result:
    args = [
        "flight",
        "add",
        designator,
        extra.get("day", "2025-05-12"),
        "OY-JAF",
        "BLL",
        "LGG",
        "--taxi",
        "90",
        "--trip",
        extra.get("trip", "1450"),
        "--takeoff",
        extra.get("takeoff", "2600"),
    ]
    return run(runner, book, *args)


def test_a_flight_goes_on_file(runner: CliRunner, fleet_book: Path) -> None:
    result = filed(runner, fleet_book)
    assert "filed QH412/12 BLLLGG OY-JAF fuel 2600/1450 (planned)" in result.output


def test_the_file_lists(runner: CliRunner, fleet_book: Path) -> None:
    filed(runner, fleet_book)
    result = run(runner, fleet_book, "flight", "list")
    assert "QH412" in result.output
    assert "BLLLGG" in result.output


def test_an_empty_file_says_so(runner: CliRunner, fleet_book: Path) -> None:
    assert "no flights on file" in run(runner, fleet_book, "flight", "list").output


def test_the_list_narrows_to_a_day(runner: CliRunner, fleet_book: Path) -> None:
    filed(runner, fleet_book)
    result = run(runner, fleet_book, "flight", "list", "--day", "2025-05-13")
    assert "no flights on file" in result.output


def test_the_list_narrows_to_an_aeroplane(runner: CliRunner, fleet_book: Path) -> None:
    filed(runner, fleet_book)
    assert "QH412" in run(runner, fleet_book, "flight", "list", "--tail", "OY-JAF").output


def test_a_flight_shows_its_fuel_chain(runner: CliRunner, fleet_book: Path) -> None:
    filed(runner, fleet_book)
    result = run(runner, fleet_book, "flight", "show", "QH412", "2025-05-12")
    assert "landing fuel 1150 kg" in result.output
    assert "block fuel 2690 kg" in result.output
    assert "dry operating weight 13640 kg" in result.output


def test_a_flight_moves_to_closed(runner: CliRunner, fleet_book: Path) -> None:
    filed(runner, fleet_book)
    run(runner, fleet_book, "flight", "status", "QH412", "2025-05-12", "closed")
    assert (
        "status closed" in run(runner, fleet_book, "flight", "show", "QH412", "2025-05-12").output
    )


def test_only_the_open_flights_list(runner: CliRunner, fleet_book: Path) -> None:
    filed(runner, fleet_book)
    run(runner, fleet_book, "flight", "status", "QH412", "2025-05-12", "closed")
    result = run(runner, fleet_book, "flight", "list", "--day", "2025-05-12", "--open")
    assert "no flights on file" in result.output


def test_the_fuel_figures_can_be_changed(runner: CliRunner, fleet_book: Path) -> None:
    filed(runner, fleet_book)
    result = run(runner, fleet_book, "flight", "fuel", "QH412", "2025-05-12", "--trip", "1600")
    assert "landing with 1000 kg" in result.output


def test_a_flight_can_come_off_file(runner: CliRunner, fleet_book: Path) -> None:
    filed(runner, fleet_book)
    run(runner, fleet_book, "flight", "remove", "QH412", "2025-05-12")
    assert "no flights on file" in run(runner, fleet_book, "flight", "list").output


def test_a_passenger_flight_is_recorded_as_one(runner: CliRunner, fleet_book: Path) -> None:
    run(
        runner,
        fleet_book,
        "flight",
        "add",
        "QH500",
        "2025-05-12",
        "OY-JAF",
        "BLL",
        "LGG",
        "--taxi",
        "90",
        "--trip",
        "1450",
        "--takeoff",
        "2600",
        "--passenger",
    )
    result = run(runner, fleet_book, "flight", "show", "QH500", "2025-05-12")
    assert "freighter no" in result.output


def test_the_group_is_registered_under_its_name() -> None:
    assert cli.commands["flight"] is flights.group
