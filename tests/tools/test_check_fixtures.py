import ast
from pathlib import Path

import pytest

from holdtrim.tools import check_fixtures
from holdtrim.tools.check_fixtures import (
    fixture_files,
    is_fixture,
    opens,
    problems,
    yields_outside_with,
)


def function(text: str) -> ast.FunctionDef:
    parsed = ast.parse(text).body[0]
    assert isinstance(parsed, ast.FunctionDef)
    return parsed


def written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    path = tmp_path / "test_thing.py"
    path.write_text(f'"""Tests."""\n\nimport pytest\n\n\n{body}\n')
    monkeypatch.setattr(check_fixtures, "fixture_files", lambda: [path])
    monkeypatch.setattr(check_fixtures, "where", lambda entry: entry.name)


def test_every_fixture_in_this_suite_closes_what_it_opens() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_fixtures.main() == 0


def test_the_conftest_files_are_read_as_well() -> None:
    assert any(path.name == "conftest.py" for path in fixture_files())


def test_a_decorated_fixture_is_recognised() -> None:
    assert is_fixture(function("@pytest.fixture\ndef book():\n    return 1"))
    assert is_fixture(function("@fixture\ndef book():\n    return 1"))
    assert not is_fixture(function("def book():\n    return 1"))


def test_a_fixture_that_opens_something_is_recognised() -> None:
    assert opens(function("def book():\n    return opened('x')"))
    assert opens(function("def book():\n    return sqlite3.connect('x')"))
    assert not opens(function("def book():\n    return 1"))


def test_a_yield_inside_a_with_is_not_outside_one() -> None:
    node = function("def book():\n    with opened('x') as conn:\n        yield conn")
    assert not yields_outside_with(node)


def test_a_bare_yield_is_outside_a_with() -> None:
    node = function("def book():\n    conn = connect('x')\n    yield conn")
    assert yields_outside_with(node)


def test_a_fixture_that_leaks_a_connection_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = (
        "@pytest.fixture\n"
        "def conn():\n"
        "    connection = connect('book.sqlite3')\n"
        "    yield connection\n"
    )
    written(tmp_path, monkeypatch, body)
    assert "yields from outside a with block" in problems()[0]


def test_a_fixture_that_closes_it_is_left_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = (
        "@pytest.fixture\n"
        "def conn():\n"
        "    with opened('book.sqlite3') as connection:\n"
        "        yield connection\n"
    )
    written(tmp_path, monkeypatch, body)
    assert problems() == []


def test_a_fixture_that_opens_nothing_is_left_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written(tmp_path, monkeypatch, "@pytest.fixture\ndef book():\n    yield 1\n")
    assert problems() == []
