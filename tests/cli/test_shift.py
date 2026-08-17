"""One shift, worked end to end through the command line.

Every other test here holds one thing still and pushes on another. This one
does what the office does, in order, and it is the only test that would notice
two commands that each work and do not work together.
"""

from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim.schedule.document import save_schedule
from tests.cli.conftest import invoke
from tests.fleet.test_type_store import a_type

DAY = "2025-05-12"


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    result = invoke(runner, book, *args)
    assert result.exception is None, f"{' '.join(args)} raised {result.exception!r}"
    return result


def set_up(runner: CliRunner, book: Path, tmp_path: Path) -> None:
    schedule = save_schedule(a_type(), tmp_path / "at7f.json")
    run(runner, book, "init")
    run(runner, book, "station", "add", "BLL", "Billund", "--elevation", "247")
    run(runner, book, "station", "add", "LGG", "Liege", "--elevation", "659")
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
    for code in ("PMC12345QH", "PMC12346QH"):
        run(
            runner,
            book,
            "uld",
            "add",
            code,
            "--tare",
            "110",
            "--max-gross",
            "4626",
            "--at",
            "BLL",
        )


def book_cargo(runner: CliRunner, book: Path) -> None:
    run(
        runner,
        book,
        "cargo",
        "book",
        "125-12345675",
        "BLL",
        "LGG",
        "--pieces",
        "8",
        "--weight",
        "1240",
        "--volume",
        "4.2",
        "--commodity",
        "machine parts",
        "--ready",
        "2025-05-11",
        "--shc",
        "RFL",
    )
    run(
        runner,
        book,
        "danger",
        "declare",
        "125-12345675",
        "--un",
        "1263",
        "--name",
        "Paint",
        "--hazard",
        "3",
        "--packages",
        "4",
        "--quantity",
        "5",
        "--unit",
        "L",
        "--pg",
        "II",
    )


def file_flight(runner: CliRunner, book: Path) -> None:
    run(
        runner,
        book,
        "flight",
        "add",
        "QH412",
        DAY,
        "OY-JAF",
        "BLL",
        "LGG",
        "--taxi",
        "90",
        "--trip",
        "1450",
        "--takeoff",
        "2600",
    )


def test_a_whole_shift_runs_through_the_command_line(
    runner: CliRunner, book: Path, tmp_path: Path
) -> None:
    set_up(runner, book, tmp_path)
    book_cargo(runner, book)
    file_flight(runner, book)

    assert (
        "may go on QH412/12"
        in run(runner, book, "cargo", "accept", "125-12345675", "QH412", DAY).output
    )

    run(runner, book, "plan", "auto", "QH412", DAY, "--load", "PMC12345QH=1350")
    assert "passes every check" in run(runner, book, "plan", "check", "QH412", DAY).output
    assert (
        "screens clean"
        in run(runner, book, "danger", "screen", "QH412", DAY, "--place", "125-12345675=11P").output
    )

    assert "LOADSHEET" in run(runner, book, "sheet", "print", "QH412", DAY, "--by", "K R").output
    assert (
        "issued QH412/12" in run(runner, book, "sheet", "issue", "QH412", DAY, "--by", "K R").output
    )
    assert "edition 1" in run(runner, book, "sheet", "history", "QH412", DAY).output

    wire = ["--to", "LGGKLQH", "--from", "BLLLDQH", "--filed", "121815"]
    assert "LDM" in run(runner, book, "message", "plan", "QH412", DAY, *wire).output
    run(runner, book, "uld", "move", "PMC12345QH", "LGG", "--on", DAY, "--flight", "QH412")
    assert "has gone" in run(runner, book, "flight", "depart", "QH412", DAY).output

    assert "carried 1350 kg" in run(runner, book, "report", "day", "--", DAY).output
    assert "FLIGHT FILE" in run(runner, book, "report", "flight", "QH412", DAY).output
    assert "nothing wrong with the book" in run(runner, book, "book", "doctor").output


def test_the_shift_leaves_the_book_verifiable(
    runner: CliRunner, book: Path, tmp_path: Path
) -> None:
    set_up(runner, book, tmp_path)
    book_cargo(runner, book)
    file_flight(runner, book)
    run(runner, book, "plan", "auto", "QH412", DAY, "--load", "PMC12345QH=1350")
    run(runner, book, "sheet", "issue", "QH412", DAY, "--by", "K R")
    assert "the book is sound" in run(runner, book, "book", "verify").output
    counts = run(runner, book, "book", "counts").output
    assert "loadsheet 1" in counts
    assert "sector 1" in counts


def test_the_shift_exports_and_reads_back(runner: CliRunner, book: Path, tmp_path: Path) -> None:
    set_up(runner, book, tmp_path)
    book_cargo(runner, book)
    file_flight(runner, book)
    run(runner, book, "plan", "auto", "QH412", DAY, "--load", "PMC12345QH=1350")
    out = tmp_path / "out"
    run(runner, book, "report", "export", str(out))
    assert (out / "consignment.csv").exists()
    assert "12512345675" in (out / "consignment.csv").read_text(encoding="utf-8")
