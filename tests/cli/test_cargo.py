from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim.cli import cargo
from holdtrim.cli.main import cli


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return runner.invoke(cli, ["--book", str(book), *args])


def booked(runner: CliRunner, book: Path, awb: str = "125-12345675", **extra: str) -> Result:
    args = [
        "cargo",
        "book",
        awb,
        "BLL",
        "LGG",
        "--pieces",
        extra.get("pieces", "8"),
        "--weight",
        extra.get("weight", "1240"),
        "--volume",
        extra.get("volume", "4.2"),
        "--commodity",
        "machine parts",
        "--ready",
        extra.get("ready", "2025-05-12"),
    ]
    if "shc" in extra:
        args.extend(["--shc", extra["shc"]])
    return run(runner, book, *args)


def prepared(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")


def test_a_waybill_goes_on_file(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    result = booked(runner, book)
    assert "booked 125-12345675 BLLLGG 8/1240" in result.output


def test_the_file_lists(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    booked(runner, book)
    result = run(runner, book, "cargo", "list")
    assert "125-12345675" in result.output
    assert "BLLLGG" in result.output


def test_an_empty_file_says_so(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    assert "no waybills on file" in run(runner, book, "cargo", "list").output


def test_the_list_narrows_to_a_sector(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    booked(runner, book)
    result = run(runner, book, "cargo", "list", "--from", "BLL", "--to", "CDG")
    assert "no waybills on file" in result.output


def test_the_list_narrows_to_what_is_ready(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    booked(runner, book, ready="2025-05-14")
    result = run(
        runner, book, "cargo", "list", "--from", "BLL", "--to", "LGG", "--ready-by", "2025-05-12"
    )
    assert "no waybills on file" in result.output


def test_a_waybill_shows_its_chargeable_weight(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    booked(runner, book, weight="400", volume="6")
    result = run(runner, book, "cargo", "show", "125-12345675")
    assert "volumetric weight 1002 kg" in result.output
    assert "chargeable weight 1002 kg" in result.output


def test_the_handling_codes_show_with_their_meaning(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    booked(runner, book, shc="PER RFL")
    result = run(runner, book, "cargo", "show", "125-12345675")
    assert "handling PER perishable" in result.output
    assert "handling RFL flammable liquid" in result.output


def test_a_handling_code_this_build_does_not_know_is_refused(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    result = booked(runner, book, shc="ZZZ")
    assert result.exception is not None


def test_the_tonnage_over_a_sector_reads_back(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    booked(runner, book, "125-12345675")
    booked(runner, book, "125-20000046", weight="760")
    result = run(runner, book, "cargo", "tonnage", "BLL", "LGG")
    assert "BLLLGG 2 waybill(s) 2000 kg" in result.output


def test_a_waybill_can_come_off_file(runner: CliRunner, book: Path) -> None:
    prepared(runner, book)
    booked(runner, book)
    run(runner, book, "cargo", "remove", "125-12345675")
    assert "no waybills on file" in run(runner, book, "cargo", "list").output


def test_the_group_is_registered_under_its_name() -> None:
    assert cli.commands["cargo"] is cargo.group
