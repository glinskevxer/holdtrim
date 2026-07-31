import pytest

from holdtrim.tools import check_readme
from holdtrim.tools.check_readme import (
    blocks,
    commands,
    paths,
    problems,
    undocumented_groups,
)


def readme() -> str:
    return check_readme.README.read_text(encoding="utf-8")


def test_the_readme_names_only_commands_that_exist() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_readme.main() == 0


def test_the_indented_lines_are_the_ones_read() -> None:
    found = blocks(readme())
    assert any(line.startswith("holdtrim --book") for line in found)
    assert not any(line.startswith("This is the office") for line in found)


def test_a_continued_command_is_joined_up() -> None:
    text = "    holdtrim tail add OY-JAF AT7F \\\n        --dow 13640\n"
    assert blocks(text) == ["holdtrim tail add OY-JAF AT7F --dow 13640"]


def test_the_commands_are_picked_out_of_the_blocks() -> None:
    found = commands(readme())
    assert any("plan auto" in line for line in found)
    assert all(line.startswith("holdtrim ") for line in found)


def test_the_paths_are_picked_out_of_the_blocks() -> None:
    found = paths(readme())
    assert "src/holdtrim/units.py" in found
    assert "tests/" in found


def test_a_command_that_is_gone_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_readme, "commands", lambda _text: ["holdtrim station invent"])
    assert "is not a command" in problems()[0]


def test_a_path_that_is_gone_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_readme, "paths", lambda _text: ["src/holdtrim/nowhere.py"])
    assert "which is not there" in problems()[0]


def test_every_group_is_in_the_operating_guide() -> None:
    assert undocumented_groups() == []


def test_a_group_the_guide_leaves_out_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_readme, "OPERATING", check_readme.OPERATING.parent / "nothing.md")
    assert "no operating guide" in undocumented_groups()[0]


def test_a_missing_readme_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_readme, "README", check_readme.README.parent / "nothing.md")
    assert "there is no README" in problems()[0]


def test_the_guide_names_every_group_it_has_to() -> None:
    text = check_readme.OPERATING.read_text(encoding="utf-8")
    for name in ("book", "cargo", "danger", "flight", "plan", "sheet", "message", "report"):
        assert f"`{name}` group" in text


def test_an_option_is_not_read_as_a_path() -> None:
    assert paths("    --book night.sqlite3 station list\n") == []


def test_a_book_file_is_not_read_as_a_path() -> None:
    assert paths("    night.sqlite3 is the book\n") == []
