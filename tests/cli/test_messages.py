from pathlib import Path

from click.testing import CliRunner, Result

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


def wire(*args: str) -> list[str]:
    return ["--to", "LGGKLQH", "--from", "BLLLDQH", "--filed", "121815", *args]


def test_the_ldm_prints(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "message", "ldm", "QH412", "2025-05-12", *wire())
    assert "LDM" in result.output
    assert "-LGG.0/0/0.T2000" in result.output


def test_the_ldm_carries_the_envelope(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "message", "ldm", "QH412", "2025-05-12", *wire())
    assert result.output.startswith("QU LGGKLQH")
    assert ".BLLLDQH 121815" in result.output


def test_the_cpm_prints_the_position(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "message", "cpm", "QH412", "2025-05-12", *wire())
    assert ".11P/PMC12345QH/2000/LGG" in result.output


def test_the_cpm_lists_the_empty_positions(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "message", "cpm", "QH412", "2025-05-12", *wire())
    assert "NIL 21P 51" in result.output


def test_the_ucm_reports_movements(runner: CliRunner, flight_book: Path) -> None:
    result = run(
        runner,
        flight_book,
        "message",
        "ucm",
        "QH412",
        "2025-05-12",
        *wire("--off", "PMC12345QH/L", "--on", "PMC12346QH/E"),
    )
    assert "OFF.PMC12345QH/L" in result.output
    assert "ON.PMC12346QH/E" in result.output


def test_a_movement_that_is_not_a_pair_is_refused(runner: CliRunner, flight_book: Path) -> None:
    result = run(
        runner,
        flight_book,
        "message",
        "ucm",
        "QH412",
        "2025-05-12",
        *wire("--off", "PMC12345QH"),
    )
    assert result.exception is not None


def test_a_ucm_with_nothing_to_report_is_refused(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "message", "ucm", "QH412", "2025-05-12", *wire())
    assert result.exception is not None


def test_both_messages_come_out_together(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "message", "plan", "QH412", "2025-05-12", *wire())
    assert "LDM" in result.output
    assert "CPM" in result.output
    assert result.output.count("QU LGGKLQH") == 2


def test_a_bad_address_is_refused(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(
        runner,
        flight_book,
        "message",
        "ldm",
        "QH412",
        "2025-05-12",
        "--to",
        "LGG",
        "--from",
        "BLLLDQH",
        "--filed",
        "121815",
    )
    assert result.exception is not None
