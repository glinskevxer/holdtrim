import pytest

from holdtrim.tools import check_design
from holdtrim.tools.check_design import exists, named, packages, problems


def test_the_design_note_describes_this_package() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_design.main() == 0


def test_the_modules_the_note_names_are_found() -> None:
    found = named(check_design.DESIGN.read_text(encoding="utf-8"))
    assert "holdtrim.units" in found
    assert "holdtrim.tools.check_layers" in found


def test_every_package_is_found() -> None:
    found = packages()
    assert "holdtrim.model" in found
    assert "holdtrim.store" in found
    assert "holdtrim.units" not in found


def test_a_module_that_is_there_exists() -> None:
    assert exists("holdtrim.units")
    assert exists("holdtrim.model.aircraft")
    assert exists("holdtrim.model")


def test_a_module_that_is_gone_does_not() -> None:
    assert not exists("holdtrim.model.nowhere")


def test_a_note_naming_a_module_that_is_gone_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_design, "named", lambda _text: ["holdtrim.model.nowhere"])
    monkeypatch.setattr(check_design, "packages", list)
    assert "which is not there" in problems()[0]


def test_a_package_the_note_leaves_out_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_design, "named", lambda _text: [])
    monkeypatch.setattr(check_design, "packages", lambda: ["holdtrim.somewhere"])
    assert "never mentions it" in problems()[0]


def test_a_missing_note_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_design, "DESIGN", check_design.DESIGN.parent / "nothing.md")
    assert "there is no design note" in problems()[0]
