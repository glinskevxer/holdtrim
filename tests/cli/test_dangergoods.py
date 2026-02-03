from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim.cli import dangergoods
from holdtrim.cli.main import cli
from tests.cli.conftest import invoke

AWB = "125-12345675"


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return invoke(runner, book, *args)


def booked(runner: CliRunner, book: Path) -> None:
    run(
        runner,
        book,
        "cargo",
        "book",
        AWB,
        "BLL",
        "LGG",
        "--pieces",
        "4",
        "--weight",
        "400",
        "--volume",
        "1.2",
        "--commodity",
        "paint",
        "--ready",
        "2025-05-11",
        "--shc",
        "RFL",
    )


def declared(runner: CliRunner, book: Path, hazard: str = "3", **extra: str) -> Result:
    args = [
        "danger",
        "declare",
        AWB,
        "--un",
        "1263",
        "--name",
        "Paint",
        "--hazard",
        hazard,
        "--packages",
        "4",
        "--quantity",
        "5",
        "--unit",
        extra.get("unit", "L"),
        "--pg",
        extra.get("pg", "II"),
    ]
    if "cao" in extra:
        args.append("--cao")
    if "ti" in extra:
        args.extend(["--ti", extra["ti"]])
    return run(runner, book, *args)


def planned(runner: CliRunner, book: Path, position: str = "11P", uld: str = "PMC12345QH") -> None:
    args = [
        "plan",
        "put",
        "QH412",
        "2025-05-12",
        position,
        "--weight",
        "400",
        "--to",
        "LGG",
    ]
    if uld:
        args.extend(["--uld", uld])
    run(runner, book, *args)


def test_the_class_table_prints(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "danger", "classes")
    assert "5.1" in result.output
    assert "oxidiser" in result.output


def test_one_class_reads_back_its_name(runner: CliRunner, flight_book: Path) -> None:
    assert "flammable liquid" in run(runner, flight_book, "danger", "meaning", "3").output


def test_a_line_is_declared_against_a_waybill(runner: CliRunner, flight_book: Path) -> None:
    booked(runner, flight_book)
    result = declared(runner, flight_book)
    assert "declared UN 1263 Paint 3 PG II 4 x 5.000 L" in result.output


def test_a_declaration_against_a_waybill_that_is_not_on_file_is_refused(
    runner: CliRunner, flight_book: Path
) -> None:
    assert declared(runner, flight_book).exception is not None


def test_the_declarations_list(runner: CliRunner, flight_book: Path) -> None:
    booked(runner, flight_book)
    declared(runner, flight_book)
    result = run(runner, flight_book, "danger", "list")
    assert "1263" in result.output
    assert "Paint" in result.output


def test_nothing_declared_says_so(runner: CliRunner, flight_book: Path) -> None:
    assert "nothing is declared" in run(runner, flight_book, "danger", "list").output


def test_a_clean_load_screens_clean(runner: CliRunner, flight_book: Path) -> None:
    booked(runner, flight_book)
    declared(runner, flight_book)
    planned(runner, flight_book)
    result = run(
        runner, flight_book, "danger", "screen", "QH412", "2025-05-12", "--place", f"{AWB}=11P"
    )
    assert "screens clean" in result.output


def test_a_cargo_only_shipment_on_a_passenger_flight_is_refused(
    runner: CliRunner, flight_book: Path
) -> None:
    booked(runner, flight_book)
    declared(runner, flight_book, cao="yes")
    run(
        runner,
        flight_book,
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
    result = run(
        runner, flight_book, "danger", "screen", "QH500", "2025-05-12", "--place", f"{AWB}=11P"
    )
    assert "cargo aircraft only" in result.output
    assert result.exit_code == 6


def test_a_place_that_is_not_a_pair_is_refused(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "danger", "screen", "QH412", "2025-05-12", "--place", AWB)
    assert result.exception is not None


def test_the_notice_prints(runner: CliRunner, flight_book: Path) -> None:
    booked(runner, flight_book)
    declared(runner, flight_book)
    planned(runner, flight_book)
    result = run(
        runner,
        flight_book,
        "danger",
        "notoc",
        "QH412",
        "2025-05-12",
        "--by",
        "K Ravn",
        "--place",
        f"{AWB}=11P",
    )
    assert "NOTIFICATION TO CAPTAIN" in result.output
    assert "commander signature" in result.output
    assert "Paint" in result.output


def test_a_notice_with_nothing_on_board_says_so(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "danger", "notoc", "QH412", "2025-05-12", "--by", "K Ravn")
    assert "no dangerous goods on board" in result.output


def test_the_declarations_can_be_cleared(runner: CliRunner, flight_book: Path) -> None:
    booked(runner, flight_book)
    declared(runner, flight_book)
    result = run(runner, flight_book, "danger", "clear", AWB)
    assert "cleared 1 line(s)" in result.output


def test_the_group_is_registered_under_its_name() -> None:
    assert cli.commands["danger"] is dangergoods.group
