from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim.cli import sheets
from holdtrim.cli.main import cli
from tests.cli.conftest import invoke


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return invoke(runner, book, *args)


def planned(runner: CliRunner, book: Path, weight: str = "2000") -> None:
    run(
        runner,
        book,
        "plan",
        "put",
        "QH412",
        "2025-05-12",
        "11P",
        "--weight",
        weight,
        "--uld",
        "PMC12345QH",
        "--to",
        "LGG",
    )


def test_the_sheet_prints_for_a_planned_flight(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "sheet", "print", "QH412", "2025-05-12", "--by", "K Ravn")
    assert "LOADSHEET" in result.output
    assert "K Ravn" in result.output
    assert "zero fuel weight" in result.output


def test_the_printed_sheet_carries_the_distribution(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "sheet", "print", "QH412", "2025-05-12", "--by", "K Ravn")
    assert "11P PMC12345QH" in result.output


def test_a_last_minute_change_reaches_the_printed_sheet(
    runner: CliRunner, flight_book: Path
) -> None:
    planned(runner, flight_book)
    result = run(
        runner,
        flight_book,
        "sheet",
        "print",
        "QH412",
        "2025-05-12",
        "--by",
        "K Ravn",
        "--lmc",
        "11P=-200",
    )
    assert "offloaded 200 kg at 11P" in result.output


def test_a_change_that_is_not_a_pair_is_refused(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(
        runner,
        flight_book,
        "sheet",
        "print",
        "QH412",
        "2025-05-12",
        "--by",
        "K Ravn",
        "--lmc",
        "11P",
    )
    assert result.exception is not None


def test_the_lmc_tolerance_comes_off_the_settings(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    run(runner, flight_book, "setting", "set", "lmc.tolerance", "100")
    result = run(
        runner,
        flight_book,
        "sheet",
        "print",
        "QH412",
        "2025-05-12",
        "--by",
        "K Ravn",
        "--lmc",
        "11P=-200",
    )
    assert "past tolerance by" in result.output


def test_a_change_inside_the_set_tolerance_is_not_flagged(
    runner: CliRunner, flight_book: Path
) -> None:
    planned(runner, flight_book)
    run(runner, flight_book, "setting", "set", "lmc.tolerance", "900")
    result = run(
        runner,
        flight_book,
        "sheet",
        "print",
        "QH412",
        "2025-05-12",
        "--by",
        "K Ravn",
        "--lmc",
        "11P=-200",
    )
    assert "past tolerance by" not in result.output


def test_a_change_with_no_number_is_refused(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(
        runner,
        flight_book,
        "sheet",
        "print",
        "QH412",
        "2025-05-12",
        "--by",
        "K Ravn",
        "--lmc",
        "11P=lots",
    )
    assert result.exception is not None


def test_the_summary_is_one_line(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "sheet", "summary", "QH412", "2025-05-12")
    assert result.output.count("\n") == 1
    assert "ZFW 15640" in result.output


def test_a_legal_sheet_issues_and_closes_the_flight(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "sheet", "issue", "QH412", "2025-05-12", "--by", "K Ravn")
    assert "issued QH412/12 OY-JAF edition 1" in result.output
    shown = run(runner, flight_book, "flight", "show", "QH412", "2025-05-12")
    assert "status closed" in shown.output


def test_a_sheet_with_a_finding_will_not_issue(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book, weight="3400")
    result = run(runner, flight_book, "sheet", "issue", "QH412", "2025-05-12", "--by", "K Ravn")
    assert result.exception is not None


def test_an_issued_sheet_goes_on_the_record(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    run(runner, flight_book, "sheet", "issue", "QH412", "2025-05-12", "--by", "K Ravn")
    result = run(runner, flight_book, "sheet", "history", "QH412", "2025-05-12")
    assert "edition 1 issued 2025-05-12 by K Ravn" in result.output


def test_the_edition_follows_what_was_already_issued(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    run(runner, flight_book, "sheet", "issue", "QH412", "2025-05-12", "--by", "K Ravn")
    run(runner, flight_book, "flight", "status", "QH412", "2025-05-12", "planned")
    result = run(runner, flight_book, "sheet", "issue", "QH412", "2025-05-12", "--by", "K Ravn")
    assert "edition 2" in result.output


def test_a_flight_with_no_loadsheet_says_so(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "sheet", "history", "QH412", "2025-05-12")
    assert "no loadsheet has been issued" in result.output


def test_the_findings_command_lists_what_is_in_the_way(
    runner: CliRunner, flight_book: Path
) -> None:
    planned(runner, flight_book, weight="3400")
    result = run(runner, flight_book, "sheet", "findings", "QH412", "2025-05-12")
    assert "position 11P" in result.output
    assert result.exit_code == 6


def test_a_clean_flight_says_it_may_be_issued(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "sheet", "findings", "QH412", "2025-05-12")
    assert "may be issued" in result.output


def test_the_group_is_registered_under_its_name() -> None:
    assert cli.commands["sheet"] is sheets.group
