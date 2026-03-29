import json
from pathlib import Path

import pytest

from holdtrim.tools import coverage_gate


def report(**files: float) -> dict[str, object]:
    covered = files or {"src/holdtrim/units.py": 99.0}
    average = sum(covered.values()) / len(covered)
    return {
        "totals": {"percent_covered": average},
        "files": {
            name: {"summary": {"percent_covered": percentage}}
            for name, percentage in covered.items()
        },
    }


def written(tmp_path: Path, **files: float) -> Path:
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(report(**files)), encoding="utf-8")
    return path


def test_a_report_that_is_not_there_says_how_to_make_one(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no coverage report"):
        coverage_gate.read(tmp_path / "missing.json")


def test_the_total_reads_off_the_report() -> None:
    assert coverage_gate.total(report()) == 99.0


def test_a_report_with_no_totals_is_refused() -> None:
    with pytest.raises(SystemExit, match="no totals"):
        coverage_gate.total({"totals": "nothing"})


def test_a_report_with_no_files_is_refused() -> None:
    with pytest.raises(SystemExit, match="no files"):
        coverage_gate.per_file({"files": "nothing"})


def test_the_per_file_figures_read_off_the_report() -> None:
    covered = coverage_gate.per_file(report(**{"a.py": 90.0, "b.py": 80.0}))
    assert covered == {"a.py": 90.0, "b.py": 80.0}


def test_the_worst_files_come_back_worst_first() -> None:
    covered = {"a.py": 90.0, "b.py": 80.0, "c.py": 99.0}
    assert coverage_gate.worst(covered, 2) == [("b.py", 80.0), ("a.py", 90.0)]


def test_a_report_above_both_floors_passes() -> None:
    assert coverage_gate.problems(report(), floor=95.0, file_floor=85.0) == []


def test_a_low_total_is_reported() -> None:
    found = coverage_gate.problems(report(**{"a.py": 50.0}), floor=95.0, file_floor=10.0)
    assert "coverage is 50.00 percent" in found[0]


def test_one_low_file_behind_covered_ones_is_reported() -> None:
    covered = report(**{"a.py": 100.0, "b.py": 100.0, "c.py": 100.0, "d.py": 40.0})
    found = coverage_gate.problems(covered, floor=80.0, file_floor=85.0)
    assert len(found) == 1
    assert "d.py is 40.00 percent" in found[0]


def test_the_gate_passes_a_report_above_the_floors(tmp_path: Path) -> None:
    path = written(tmp_path)
    assert coverage_gate.main(["--report", str(path)]) == 0


def test_the_gate_fails_a_report_under_a_floor(tmp_path: Path) -> None:
    path = written(tmp_path, **{"a.py": 40.0})
    assert coverage_gate.main(["--report", str(path), "--floor", "95", "--file-floor", "85"]) == 1


def test_the_gate_prints_the_worst_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = written(tmp_path, **{"a.py": 100.0, "b.py": 91.0})
    coverage_gate.main(["--report", str(path), "--worst", "1", "--file-floor", "50"])
    printed = capsys.readouterr().out
    assert "b.py" in printed
    assert "coverage 95.50 percent over 2 files" in printed
