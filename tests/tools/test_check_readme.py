import pytest

from holdtrim.tools import check_readme
from holdtrim.tools.check_readme import blocks, commands, paths, problems


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


def test_a_missing_readme_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_readme, "README", check_readme.README.parent / "nothing.md")
    assert "there is no README" in problems()[0]
