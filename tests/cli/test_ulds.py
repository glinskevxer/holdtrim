from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim.cli import ulds
from holdtrim.cli.main import cli


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return runner.invoke(cli, ["--book", str(book), *args])


def added(runner: CliRunner, book: Path, code: str = "PMC12345QH", **extra: str) -> Result:
    args = [
        "uld",
        "add",
        code,
        "--tare",
        extra.get("tare", "110"),
        "--max-gross",
        extra.get("max_gross", "4626"),
    ]
    if "at" in extra:
        args.extend(["--at", extra["at"]])
    if "condition" in extra:
        args.extend(["--condition", extra["condition"]])
    return run(runner, book, *args)


def test_a_device_goes_on_the_register(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = added(runner, book, at="BLL")
    assert "added PMC12345QH tare 110 max 4626 BLL serviceable" in result.output


def test_the_register_lists(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    result = run(runner, book, "uld", "list")
    assert "PMC12345QH" in result.output
    assert "4516" in result.output


def test_an_empty_register_says_so(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    assert "no devices on the register" in run(runner, book, "uld", "list").output


def test_the_list_narrows_to_a_station(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    result = run(runner, book, "uld", "list", "--at", "LGG")
    assert "no devices on the register" in result.output


def test_the_list_narrows_to_serviceable_devices(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL", condition="damaged")
    result = run(runner, book, "uld", "list", "--at", "BLL", "--serviceable")
    assert "no devices on the register" in result.output


def test_a_device_shows_in_full(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    result = run(runner, book, "uld", "show", "pmc12345qh")
    assert "category certified pallet" in result.output
    assert "payload capacity 4516 kg" in result.output


def test_a_device_can_be_moved(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    result = run(runner, book, "uld", "move", "PMC12345QH", "LGG", "--on", "2025-05-12")
    assert "is now at LGG" in result.output


def test_a_move_logs_both_halves(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    run(runner, book, "uld", "move", "PMC12345QH", "LGG", "--on", "2025-05-12")
    result = run(runner, book, "uld", "log", "PMC12345QH")
    assert "BLL" in result.output
    assert "out" in result.output
    assert "LGG" in result.output


def test_a_device_that_was_nowhere_logs_only_the_arrival(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book)
    run(runner, book, "uld", "move", "PMC12345QH", "LGG", "--on", "2025-05-12")
    result = run(runner, book, "uld", "log", "PMC12345QH")
    assert result.output.count("2025-05-12") == 1


def test_a_movement_can_be_logged_on_its_own(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    result = run(
        runner,
        book,
        "uld",
        "record",
        "PMC12345QH",
        "BLL",
        "in",
        "--on",
        "2025-05-12",
        "--flight",
        "QH412/2025-05-12",
        "--note",
        "corner damage",
    )
    assert "logged 2025-05-12 BLL in PMC12345QH" in result.output
    assert "corner damage" in result.output


def test_a_device_with_no_history_says_so(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    result = run(runner, book, "uld", "log", "PMC12345QH")
    assert "nothing has ever been logged for PMC12345QH" in result.output


def test_a_condition_can_be_recorded(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    run(runner, book, "uld", "condition", "PMC12345QH", "damaged")
    assert "condition damaged" in run(runner, book, "uld", "show", "PMC12345QH").output


def test_the_stock_at_a_station_counts_by_base(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, "PMC12345QH", at="BLL")
    added(runner, book, "PMC12346QH", at="BLL")
    result = run(runner, book, "uld", "stock", "BLL")
    assert "PMC" in result.output
    assert "2" in result.output


def test_a_station_holding_nothing_says_so(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    assert "nothing is standing at CDG" in run(runner, book, "uld", "stock", "CDG").output


def test_devices_in_transit_list(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book)
    assert "PMC12345QH" in run(runner, book, "uld", "transit").output


def test_nothing_in_transit_says_so(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    assert "nothing is in transit" in run(runner, book, "uld", "transit").output


def test_a_device_can_come_off_the_register(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    added(runner, book, at="BLL")
    run(runner, book, "uld", "remove", "PMC12345QH")
    assert "no devices on the register" in run(runner, book, "uld", "list").output


def test_the_group_is_registered_under_its_name() -> None:
    assert cli.commands["uld"] is ulds.group
