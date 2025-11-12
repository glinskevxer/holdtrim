import click
import pytest

from holdtrim.cli.main import cli
from holdtrim.tools import check_help
from holdtrim.tools.check_help import problems, walk


def test_every_command_and_option_explains_itself() -> None:
    assert problems() == []


def test_the_check_passes() -> None:
    assert check_help.main() == 0


def test_the_walk_finds_the_whole_tree() -> None:
    names = [name for name, _ in walk(cli)]
    assert "cli station add" in names
    assert "cli plan auto" in names


def test_the_walk_starts_at_the_top() -> None:
    assert walk(cli)[0][0] == "cli"


def test_a_command_with_no_help_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.group()
    def bare() -> None:
        pass

    monkeypatch.setattr(check_help, "cli", bare)
    assert problems() == ["bare: the command has no help text"]


def test_an_option_with_no_help_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.group()
    def group() -> None:
        """A group."""

    @group.command()
    @click.option("--loud", help="")
    def shout(loud: str) -> None:
        """Shout."""

    monkeypatch.setattr(check_help, "cli", group)
    assert "shout: --loud has no help text" in problems()[0]


def test_help_that_does_not_end_in_a_full_stop_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @click.group()
    def group() -> None:
        """A group."""

    @group.command()
    @click.option("--loud", help="How loud")
    def shout(loud: str) -> None:
        """Shout."""

    monkeypatch.setattr(check_help, "cli", group)
    assert "does not end in a full stop" in problems()[0]


def test_help_that_starts_in_lower_case_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.group()
    def group() -> None:
        """A group."""

    @group.command()
    @click.option("--loud", help="how loud.")
    def shout(loud: str) -> None:
        """Shout."""

    monkeypatch.setattr(check_help, "cli", group)
    assert "starts in lower case" in problems()[0]
