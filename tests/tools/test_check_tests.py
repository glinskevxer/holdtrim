from pathlib import Path

import pytest

from holdtrim.tools import check_tests
from holdtrim.tools.check_tests import named_in_tests, problems


def test_every_module_is_named_by_a_test() -> None:
    assert problems() == []


def test_the_check_passes() -> None:
    assert check_tests.main() == 0


def test_the_modules_the_tests_name_are_found() -> None:
    named = named_in_tests()
    assert "holdtrim.units" in named
    assert "holdtrim.model.station" in named


def test_a_module_nothing_names_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lonely = tmp_path / "lonely.py"
    lonely.write_text('"""Nobody tests this."""\n')
    monkeypatch.setattr(check_tests, "package_files", lambda: [lonely])
    monkeypatch.setattr(check_tests, "module_name", lambda _path: "holdtrim.lonely")
    monkeypatch.setattr(check_tests, "named_in_tests", lambda: {"holdtrim.units"})
    monkeypatch.setattr(check_tests, "where", lambda path: path.name)
    assert problems() == ["lonely.py: holdtrim.lonely is not named by any test"]


def test_a_package_init_is_not_expected_to_be_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init = tmp_path / "__init__.py"
    init.write_text('"""A package."""\n')
    monkeypatch.setattr(check_tests, "package_files", lambda: [init])
    monkeypatch.setattr(check_tests, "module_name", lambda _path: "holdtrim.somewhere")
    monkeypatch.setattr(check_tests, "named_in_tests", lambda: set())
    monkeypatch.setattr(check_tests, "where", lambda path: path.name)
    assert problems() == []


def test_a_module_imported_from_its_package_counts_as_named() -> None:
    named = named_in_tests()
    assert "holdtrim.store.fleet" in named
    assert "holdtrim.cli.main" in named
