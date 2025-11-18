from pathlib import Path

import pytest

from holdtrim.tools import smoke


def test_the_example_type_is_a_whole_schedule() -> None:
    kind = smoke.example_type()
    assert kind.code == "AT7F"
    assert len(kind.layout.positions) == 3
    assert kind.fuel.capacity == 4500
    assert kind.trim.forward_end is not None


def test_one_flight_runs_all_the_way_through(tmp_path: Path) -> None:
    summary = smoke.run(tmp_path / "smoke.sqlite3", quiet=True)
    assert "QH412/12 OY-JAF" in summary
    assert "ZFW 15940" in summary


def test_the_run_leaves_a_book_behind(tmp_path: Path) -> None:
    path = tmp_path / "smoke.sqlite3"
    smoke.run(path, quiet=True)
    assert path.exists()


def test_the_summary_prints_unless_asked_not_to(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    smoke.run(tmp_path / "smoke.sqlite3")
    assert "trim" in capsys.readouterr().out


def test_the_command_makes_its_own_book_and_throws_it_away(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert smoke.main([]) == 0
    assert "smoke test passed" in capsys.readouterr().out


def test_the_command_can_be_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    assert smoke.main(["--quiet"]) == 0
    assert capsys.readouterr().out == ""
