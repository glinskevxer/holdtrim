import pytest

from holdtrim import __version__
from holdtrim.tools import release_check
from holdtrim.tools.release_check import changelog_versions, problems, project_version


def test_the_version_agrees_everywhere() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert release_check.main() == 0


def test_the_project_file_declares_the_package_version() -> None:
    assert project_version() == __version__


def test_the_changelog_has_a_section_for_it() -> None:
    assert changelog_versions()[0] == __version__


def test_a_version_that_is_not_one_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release_check, "project_version", lambda: "one")
    assert "which is not a version" in problems()[0]


def test_a_package_that_disagrees_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release_check, "project_version", lambda: "9.9.9")
    assert any("the package says" in problem for problem in problems())


def test_a_changelog_with_no_sections_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release_check, "changelog_versions", list)
    assert any("no version sections" in problem for problem in problems())


def test_a_changelog_starting_at_the_wrong_version_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release_check, "changelog_versions", lambda: ["9.9.9"])
    assert any("the changelog starts at 9.9.9" in problem for problem in problems())


def test_a_repeated_version_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release_check, "changelog_versions", lambda: [__version__, __version__])
    assert any("twice" in problem for problem in problems())
