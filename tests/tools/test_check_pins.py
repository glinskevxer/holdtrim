import pytest

from holdtrim.tools import check_pins
from holdtrim.tools.check_pins import constrained, direct, problems, unpinned


def test_the_two_files_agree() -> None:
    assert problems() == []


def test_the_check_passes() -> None:
    assert check_pins.main() == 0


def test_the_direct_dependencies_are_read() -> None:
    pinned = direct()
    assert pinned["click"] == "8.1.8"
    assert pinned["pytest"] == "8.3.4"


def test_the_constraints_carry_the_transitive_closure() -> None:
    held = constrained()
    assert "pluggy" in held
    assert "packaging" in held


def test_every_constraint_is_an_exact_pin() -> None:
    assert unpinned() == []


def test_a_dependency_missing_from_the_constraints_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_pins, "direct", lambda: {"nowhere": "1.0"})
    assert "constraints.txt does not carry it" in problems()[0]


def test_a_version_that_does_not_match_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_pins, "direct", lambda: {"click": "9.0.0"})
    assert "9.0.0 in pyproject.toml" in problems()[0]


def test_a_loose_constraint_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_pins, "unpinned", lambda: ["click>=8"])
    assert "does not pin 'click>=8' exactly" in problems()[0]
