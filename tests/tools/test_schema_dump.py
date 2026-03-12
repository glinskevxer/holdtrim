from pathlib import Path

import pytest

from holdtrim.store.migrations import MIGRATIONS
from holdtrim.tools import schema_dump
from holdtrim.tools.schema_dump import render


def test_the_written_schema_is_current() -> None:
    assert schema_dump.main(["--check"]) == 0


def test_the_dump_names_every_table() -> None:
    text = render()
    for table in ("station", "aircraft_type", "tail", "sector", "uld_movement"):
        assert f"CREATE TABLE {table} " in text


def test_the_dump_carries_the_indexes() -> None:
    assert "CREATE INDEX station_by_name" in render()


def test_the_dump_says_which_schema_version_it_is() -> None:
    assert f"schema {MIGRATIONS[-1].version}" in render()


def test_every_statement_is_one_line() -> None:
    for line in render().splitlines():
        if line.startswith("CREATE"):
            assert line.endswith(";")


def test_writing_the_dump_puts_it_where_asked(tmp_path: Path) -> None:
    out = tmp_path / "deep" / "schema.sql"
    assert schema_dump.main(["--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == render()


def test_a_dump_that_was_never_written_fails_the_check(tmp_path: Path) -> None:
    assert schema_dump.main(["--check", "--out", str(tmp_path / "nothing.sql")]) == 1


def test_a_stale_dump_fails_the_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "schema.sql"
    out.write_text("out of date", encoding="utf-8")
    assert schema_dump.main(["--check", "--out", str(out)]) == 1
    assert "out of date" in capsys.readouterr().out
