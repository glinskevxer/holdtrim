from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from holdtrim.cli.main import cli
from holdtrim.schedule.document import save_schedule
from tests.fleet.test_type_store import a_type


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return runner.invoke(cli, ["--book", str(book), *args])


@pytest.fixture
def schedule(tmp_path: Path) -> Path:
    return save_schedule(a_type(), tmp_path / "at7f.json")


def prepared(runner: CliRunner, book: Path, schedule: Path) -> None:
    run(runner, book, "init")
    run(runner, book, "fleet", "load", str(schedule))


def test_a_schedule_registers_the_type(runner: CliRunner, book: Path, schedule: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "fleet", "load", str(schedule))
    assert "registered AT7F" in result.output


def test_the_registered_types_list(runner: CliRunner, book: Path, schedule: Path) -> None:
    prepared(runner, book, schedule)
    result = run(runner, book, "fleet", "types")
    assert "AT7F" in result.output
    assert "20800" in result.output


def test_an_empty_register_says_so(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    assert "no types in the fleet register" in run(runner, book, "fleet", "types").output


def test_a_type_shows_its_certificate_weights(
    runner: CliRunner, book: Path, schedule: Path
) -> None:
    prepared(runner, book, schedule)
    result = run(runner, book, "fleet", "show", "at7f")
    assert "max zero fuel 20800 kg" in result.output
    assert "taxi allowance 250 kg" in result.output
    assert "structural payload 7700 kg" in result.output


def test_the_positions_print_front_to_back(runner: CliRunner, book: Path, schedule: Path) -> None:
    prepared(runner, book, schedule)
    result = run(runner, book, "fleet", "positions", "AT7F")
    lines = [line for line in result.output.splitlines() if line.startswith(("11P", "21P", "51"))]
    assert [line.split()[0] for line in lines] == ["11P", "21P", "51"]


def test_a_bulk_position_prints_as_bulk(runner: CliRunner, book: Path, schedule: Path) -> None:
    prepared(runner, book, schedule)
    assert "bulk" in run(runner, book, "fleet", "positions", "AT7F").output


def test_the_combined_limits_print_under_the_positions(
    runner: CliRunner, book: Path, schedule: Path
) -> None:
    prepared(runner, book, schedule)
    result = run(runner, book, "fleet", "positions", "AT7F")
    assert "combined 11P+21P max 5400 kg" in result.output


def test_an_envelope_prints_its_breakpoints(runner: CliRunner, book: Path, schedule: Path) -> None:
    prepared(runner, book, schedule)
    result = run(runner, book, "fleet", "envelope", "AT7F", "takeoff")
    assert "13000" in result.output
    assert "36.0" in result.output


def test_an_envelope_the_type_has_not_got_raises(
    runner: CliRunner, book: Path, schedule: Path
) -> None:
    prepared(runner, book, schedule)
    result = run(runner, book, "fleet", "envelope", "AT7F", "ferry")
    assert result.exception is not None


def test_a_type_dumps_back_out_to_a_document(
    runner: CliRunner, book: Path, schedule: Path, tmp_path: Path
) -> None:
    prepared(runner, book, schedule)
    out = tmp_path / "again.json"
    run(runner, book, "fleet", "dump", "AT7F", str(out))
    assert out.read_text() == schedule.read_text()


def test_a_type_can_be_removed(runner: CliRunner, book: Path, schedule: Path) -> None:
    prepared(runner, book, schedule)
    run(runner, book, "fleet", "remove", "AT7F")
    assert "no types in the fleet register" in run(runner, book, "fleet", "types").output
