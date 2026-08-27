import pytest

from holdtrim.tools import check_package
from holdtrim.tools.check_package import (
    points_at_something,
    problems,
    scripts,
    wheel_packages,
)


def test_the_package_would_install_as_what_it_says() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_package.main() == 0


def test_the_typing_marker_is_in_the_package() -> None:
    assert check_package.MARKER.exists()


def test_the_wheel_is_told_to_take_the_source_directory() -> None:
    assert wheel_packages() == ["src/holdtrim"]


def test_the_console_script_is_declared() -> None:
    assert scripts()["holdtrim"] == "holdtrim.cli.main:run"


def test_a_script_target_that_is_there_points_at_something() -> None:
    assert points_at_something("holdtrim.cli.main:run")


def test_a_script_target_in_a_module_that_is_gone_does_not() -> None:
    assert not points_at_something("holdtrim.nowhere:run")


def test_a_script_target_with_no_such_function_does_not() -> None:
    assert not points_at_something("holdtrim.cli.main:fly")


def test_a_missing_typing_marker_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_package, "MARKER", check_package.MARKER.parent / "nothing")
    assert "no py.typed" in problems()[0]


def test_a_wheel_told_to_take_the_wrong_directory_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_package, "wheel_packages", lambda: ["src/elsewhere"])
    assert "does not include src/holdtrim" in problems()[0]


def test_a_project_with_no_console_script_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_package, "scripts", dict)
    assert any("no console script" in problem for problem in problems())


def test_a_script_pointing_at_nothing_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_package, "scripts", lambda: {"holdtrim": "holdtrim.nowhere:run"})
    assert any("which is not there" in problem for problem in problems())
