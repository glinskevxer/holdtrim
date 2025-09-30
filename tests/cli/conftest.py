from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from holdtrim.cli.main import cli
from holdtrim.schedule.document import save_schedule
from tests.fleet.test_type_store import a_type


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def book(tmp_path: Path) -> Path:
    return tmp_path / "book.sqlite3"


def invoke(runner: CliRunner, book: Path, *args: str) -> Result:
    return runner.invoke(cli, ["--book", str(book), *args])


@pytest.fixture
def flight_book(runner: CliRunner, book: Path, tmp_path: Path) -> Path:
    """A book with a type, an aeroplane, a flight and two devices in it."""
    schedule = save_schedule(a_type(), tmp_path / "at7f.json")
    invoke(runner, book, "init")
    invoke(runner, book, "fleet", "load", str(schedule))
    invoke(
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
    invoke(
        runner,
        book,
        "flight",
        "add",
        "QH412",
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
    )
    for code in ("PMC12345QH", "PMC12346QH"):
        invoke(
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
    return book
