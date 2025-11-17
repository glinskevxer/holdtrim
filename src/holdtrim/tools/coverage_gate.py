"""The coverage floor, read off the report rather than trusted.

Two floors, not one. A whole project figure hides a module with no tests at
all behind a hundred well covered ones, so there is a per file floor as well,
and it is the one that has ever actually caught anything.

The gate also prints the worst files whether or not it fails. A number that
only appears when something is broken is a number nobody watches drift.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_REPORT = Path("coverage.json")
DEFAULT_FLOOR = 95.0
DEFAULT_FILE_FLOOR = 85.0
DEFAULT_WORST = 5


def read(path: Path) -> dict[str, object]:
    """Read the coverage report, saying plainly when it is not there."""
    if not path.exists():
        raise SystemExit(f"no coverage report at {path}, run pytest --cov --cov-report=json")
    parsed: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return parsed


def total(report: dict[str, object]) -> float:
    """The whole project percentage."""
    totals = report.get("totals", {})
    if not isinstance(totals, dict):
        raise SystemExit("the coverage report has no totals in it")
    return float(totals.get("percent_covered", 0.0))


def per_file(report: dict[str, object]) -> dict[str, float]:
    """Each file's percentage, worst first when sorted."""
    files = report.get("files", {})
    if not isinstance(files, dict):
        raise SystemExit("the coverage report has no files in it")
    covered = {}
    for name, entry in files.items():
        summary = entry.get("summary", {}) if isinstance(entry, dict) else {}
        covered[str(name)] = float(summary.get("percent_covered", 0.0))
    return covered


def worst(covered: dict[str, float], how_many: int) -> list[tuple[str, float]]:
    """The least covered files, worst first."""
    return sorted(covered.items(), key=lambda pair: (pair[1], pair[0]))[:how_many]


def problems(report: dict[str, object], *, floor: float, file_floor: float) -> list[str]:
    """Everything under a floor."""
    found = []
    overall = total(report)
    if overall < floor:
        found.append(f"coverage is {overall:.2f} percent against a floor of {floor:.2f}")
    for name, percentage in sorted(per_file(report).items()):
        if percentage < file_floor:
            found.append(
                f"{name} is {percentage:.2f} percent against a file floor of {file_floor:.2f}"
            )
    return found


def main(argv: list[str] | None = None) -> int:
    """Read the report, print the worst files, and gate on the floors."""
    parser = argparse.ArgumentParser(description="Gate on the coverage report.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--floor", type=float, default=DEFAULT_FLOOR)
    parser.add_argument("--file-floor", type=float, default=DEFAULT_FILE_FLOOR)
    parser.add_argument("--worst", type=int, default=DEFAULT_WORST)
    arguments = parser.parse_args(argv)
    report = read(arguments.report)
    print(f"coverage {total(report):.2f} percent over {len(per_file(report))} files")
    for name, percentage in worst(per_file(report), arguments.worst):
        print(f"  {percentage:6.2f}  {name}")
    found = problems(report, floor=arguments.floor, file_floor=arguments.file_floor)
    for problem in found:
        print(problem)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
