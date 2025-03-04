from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def book(tmp_path: Path) -> Path:
    return tmp_path / "book.sqlite3"
