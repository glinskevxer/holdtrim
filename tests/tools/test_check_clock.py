import ast
from pathlib import Path

import pytest

from holdtrim.tools import check_clock
from holdtrim.tools.check_clock import _called_name, problems


def test_nothing_in_the_package_reads_the_clock() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_clock.main() == 0


def test_a_call_to_today_is_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('"""A file."""\n\nfrom datetime import date\n\nWHEN = date.today()\n')
    monkeypatch.setattr(check_clock, "package_files", lambda: [bad])
    monkeypatch.setattr(check_clock, "where", lambda path: path.name)
    found = problems()
    assert len(found) == 1
    assert "date.today" in found[0]


def test_a_call_to_now_is_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('"""A file."""\n\nimport datetime\n\nWHEN = datetime.datetime.now()\n')
    monkeypatch.setattr(check_clock, "package_files", lambda: [bad])
    monkeypatch.setattr(check_clock, "where", lambda path: path.name)
    assert "datetime.now" in problems()[0]


def test_importing_time_is_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('"""A file."""\n\nimport time\n')
    monkeypatch.setattr(check_clock, "package_files", lambda: [bad])
    monkeypatch.setattr(check_clock, "where", lambda path: path.name)
    assert "which is a clock" in problems()[0]


def test_a_day_passed_in_as_an_argument_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    good = tmp_path / "good.py"
    good.write_text(
        '"""A file."""\n\nfrom datetime import date\n\n\ndef due(on: date) -> date:\n'
        "    return on\n"
    )
    monkeypatch.setattr(check_clock, "package_files", lambda: [good])
    monkeypatch.setattr(check_clock, "where", lambda path: path.name)
    assert problems() == []


def test_a_plain_call_has_a_name() -> None:
    call = ast.parse("today()").body[0].value  # type: ignore[attr-defined]
    assert _called_name(call) == "today"


def test_a_call_on_something_that_is_not_a_name_has_none() -> None:
    call = ast.parse("things[0]()").body[0].value  # type: ignore[attr-defined]
    assert _called_name(call) == ""
