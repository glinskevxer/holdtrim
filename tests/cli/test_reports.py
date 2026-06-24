from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim.cli import reports
from holdtrim.cli.main import cli
from tests.cli.conftest import invoke


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return invoke(runner, book, *args)


def planned(runner: CliRunner, book: Path) -> None:
    run(
        runner,
        book,
        "plan",
        "put",
        "QH412",
        "2025-05-12",
        "11P",
        "--weight",
        "2000",
        "--uld",
        "PMC12345QH",
        "--to",
        "LGG",
    )


def test_the_stock_report_counts_by_base(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "report", "stock", "BLL")
    assert "PMC" in result.output
    assert "2" in result.output


def test_a_station_holding_nothing_says_so(runner: CliRunner, flight_book: Path) -> None:
    assert "nothing is standing at CDG" in run(runner, flight_book, "report", "stock", "CDG").output


def test_nothing_standing_says_so(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "report", "standing", "BLL", "--on", "2025-05-12")
    assert "nothing has been standing at BLL" in result.output


def test_the_free_days_come_off_the_settings(runner: CliRunner, flight_book: Path) -> None:
    run(runner, flight_book, "uld", "move", "PMC12345QH", "LGG", "--on", "2025-05-01")
    run(runner, flight_book, "setting", "set", "demurrage.free_days", "0")
    run(runner, flight_book, "setting", "set", "demurrage.daily_rate", "10")
    result = run(runner, flight_book, "report", "standing", "LGG", "--on", "2025-05-11")
    assert "owing 100" in result.output


def test_the_command_line_beats_the_settings(runner: CliRunner, flight_book: Path) -> None:
    run(runner, flight_book, "uld", "move", "PMC12345QH", "LGG", "--on", "2025-05-01")
    run(runner, flight_book, "setting", "set", "demurrage.free_days", "0")
    result = run(
        runner,
        flight_book,
        "report",
        "standing",
        "LGG",
        "--on",
        "2025-05-11",
        "--free-days",
        "20",
    )
    assert "owing 0" in result.output


def test_the_two_records_disagree_when_nothing_is_logged(
    runner: CliRunner, flight_book: Path
) -> None:
    result = run(runner, flight_book, "report", "disagreements", "BLL", "--on", "2025-05-12")
    assert "PMC" in result.output
    assert "2" in result.output


def test_a_day_with_a_flight_reports_its_capacity(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "report", "day", "2025-05-12")
    assert "QH412/12" in result.output
    assert "carried 2000 kg" in result.output
    assert "limited by" in result.output


def test_a_day_with_nothing_flying_says_so(runner: CliRunner, flight_book: Path) -> None:
    assert (
        "nothing is flying on 2025-05-13"
        in run(runner, flight_book, "report", "day", "2025-05-13").output
    )


def test_the_flight_file_prints(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "report", "flight", "QH412", "2025-05-12")
    assert "FLIGHT FILE QH412/2025-05-12" in result.output
    assert "11P PMC12345QH 2000 kg" in result.output
    assert "LOADSHEETS ISSUED" in result.output


def test_the_book_exports_to_csv(runner: CliRunner, flight_book: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = run(runner, flight_book, "report", "export", str(out))
    assert (out / "station.csv").exists()
    assert "row(s) in" in result.output


def test_a_booking_file_imports(runner: CliRunner, flight_book: Path, tmp_path: Path) -> None:
    source = tmp_path / "bookings.csv"
    source.write_text(
        "awb,origin,destination,pieces,gross_weight,volume,commodity,ready_on,handling\n"
        "125-12345675,BLL,LGG,8,1240,4.2,machine parts,2025-05-12,PER\n",
        encoding="utf-8",
    )
    result = run(runner, flight_book, "report", "import", str(source))
    assert "1 accepted, 0 rejected, 1240 kg" in result.output


def test_a_booking_file_with_a_bad_row_is_reported(
    runner: CliRunner, flight_book: Path, tmp_path: Path
) -> None:
    source = tmp_path / "bookings.csv"
    source.write_text(
        "awb,origin,destination,pieces,gross_weight,volume,commodity,ready_on,handling\n"
        "125-12345674,BLL,LGG,8,1240,4.2,machine parts,2025-05-12,\n",
        encoding="utf-8",
    )
    result = run(runner, flight_book, "report", "import", str(source))
    assert "line 2" in result.output
    assert result.exception is not None


def test_the_group_is_registered_under_its_name() -> None:
    assert cli.commands["report"] is reports.group


def test_a_period_sums_up_what_flew(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(
        runner, flight_book, "report", "period", "--from", "2025-05-01", "--to", "2025-05-31"
    )
    assert "flights 1" in result.output
    assert "carried 2000 kg" in result.output


def test_a_period_with_nothing_in_it_sums_to_nothing(runner: CliRunner, flight_book: Path) -> None:
    result = run(
        runner, flight_book, "report", "period", "--from", "2024-01-01", "--to", "2024-01-31"
    )
    assert "flights 0" in result.output


def test_the_handover_prints_for_a_station(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "report", "handover", "BLL", "--on", "2025-05-12")
    assert "HANDOVER BLL 2025-05-12" in result.output
    assert "flights still open" in result.output


def test_a_station_with_nothing_on_says_so(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "report", "handover", "CDG", "--on", "2025-05-12")
    assert "nothing to hand over" in result.output


def test_the_flow_report_counts_both_directions(runner: CliRunner, flight_book: Path) -> None:
    run(runner, flight_book, "uld", "move", "PMC12345QH", "LGG", "--on", "2025-05-12")
    result = run(
        runner, flight_book, "report", "flow", "--from", "2025-05-01", "--to", "2025-05-31"
    )
    assert "BLL" in result.output
    assert "LGG" in result.output
    assert "busiest" in result.output


def test_a_period_with_no_movements_says_so(runner: CliRunner, flight_book: Path) -> None:
    result = run(
        runner, flight_book, "report", "flow", "--from", "2024-01-01", "--to", "2024-01-31"
    )
    assert "nothing moved between" in result.output


def test_the_idle_report_lists_what_has_not_moved(runner: CliRunner, flight_book: Path) -> None:
    run(runner, flight_book, "uld", "move", "PMC12345QH", "LGG", "--on", "2025-05-01")
    result = run(runner, flight_book, "report", "idle", "--on", "2025-05-20")
    assert "PMC12345QH" in result.output


def test_nothing_idle_says_so(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "report", "idle", "--on", "2025-05-20")
    assert "nothing has been standing more than 14 days" in result.output
