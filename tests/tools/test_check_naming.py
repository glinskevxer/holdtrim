from pathlib import Path

import pytest

from holdtrim.tools import check_naming
from holdtrim.tools.check_naming import problems, words


def written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    path = tmp_path / "test_thing.py"
    path.write_text(f'"""Tests."""\n\n\n{body}\n')
    monkeypatch.setattr(check_naming, "test_files", lambda: [path])
    monkeypatch.setattr(check_naming, "where", lambda entry: entry.name)


def test_every_test_in_this_suite_reads_as_a_claim() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_naming.main() == 0


def test_the_words_of_a_name_drop_the_leading_test() -> None:
    assert words("test_a_station_normalises_its_code") == [
        "a",
        "station",
        "normalises",
        "its",
        "code",
    ]


def test_a_short_name_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written(tmp_path, monkeypatch, "def test_it_passes():\n    pass")
    assert "is 2 words" in problems()[0]


def test_a_vague_name_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written(tmp_path, monkeypatch, "def test_the_station_register_works_correctly():\n    pass")
    assert "which says nothing" in problems()[0]


def test_a_name_defined_twice_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    body = (
        "def test_a_station_keeps_its_code():\n    pass\n\n\n"
        "def test_a_station_keeps_its_code():\n    pass"
    )
    written(tmp_path, monkeypatch, body)
    assert any("defined twice" in problem for problem in problems())


def test_a_name_that_says_something_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written(tmp_path, monkeypatch, "def test_a_station_normalises_its_code():\n    pass")
    assert problems() == []


def test_a_helper_that_is_not_a_test_is_left_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written(tmp_path, monkeypatch, "def helper():\n    pass")
    assert problems() == []
