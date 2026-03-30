import pytest

from holdtrim.tools import check_workflow
from holdtrim.tools.check_workflow import (
    invocations,
    option_names,
    problems,
    resolve,
    walk_text,
)


def test_every_command_in_the_walk_is_a_real_command() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_workflow.main() == 0


def test_the_walk_is_read_out_of_the_workflow() -> None:
    found = invocations(walk_text())
    assert any(line.startswith("holdtrim --book") for line in found)
    assert len(found) > 20


def test_a_continued_line_is_joined_up() -> None:
    text = "holdtrim --book x tail add OY-JAF AT7F \\\n  --dow 13640 --doi 46.2\n"
    assert invocations(text) == ["holdtrim --book x tail add OY-JAF AT7F --dow 13640 --doi 46.2"]


def test_a_line_that_is_not_the_console_script_is_ignored() -> None:
    assert invocations("python -m pytest -q\n") == []


def test_a_real_command_resolves_past_the_book_option() -> None:
    path, missing = resolve(["--book", "x", "station", "add", "BLL"])
    assert [command.name for command in path] == ["cli", "station", "add"]
    assert missing == ""


def test_a_command_that_does_not_exist_is_named() -> None:
    path, missing = resolve(["station", "invent"])
    assert missing == "invent"
    assert [command.name for command in path] == ["cli", "station"]


def test_the_arguments_after_a_command_are_not_read_as_commands() -> None:
    path, missing = resolve(["station", "add", "BLL", "Billund"])
    assert missing == ""
    assert path[-1].name == "add"


def test_the_options_of_a_command_come_back() -> None:
    path, _ = resolve(["station", "add"])
    assert "--elevation" in option_names(path[-1])


def test_a_walk_naming_a_command_that_is_gone_is_reported() -> None:
    assert "not a command" in problems("holdtrim station invent BLL\n")[0]


def test_a_walk_passing_an_option_that_is_gone_is_reported() -> None:
    found = problems("holdtrim station add BLL Billund --height 247\n")
    assert "does not take" in found[0]


def test_a_walk_using_the_top_level_book_option_is_allowed() -> None:
    assert problems("holdtrim --book x station list\n") == []


def test_a_missing_workflow_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_workflow, "WORKFLOW", check_workflow.WORKFLOW.parent / "nowhere.yml")
    assert "there is no workflow" in problems()[0]
