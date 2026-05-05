from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim.cli import policy
from holdtrim.cli.main import cli
from tests.cli.conftest import invoke


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return invoke(runner, book, *args)


def test_the_settings_list_with_their_defaults(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "setting", "list")
    assert "lmc.tolerance" in result.output
    assert "default" in result.output


def test_a_setting_can_be_changed_and_read_back(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    run(runner, book, "setting", "set", "lmc.tolerance", "300")
    result = run(runner, book, "setting", "get", "lmc.tolerance")
    assert "lmc.tolerance 300" in result.output


def test_a_changed_setting_lists_as_set(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    run(runner, book, "setting", "set", "lmc.tolerance", "300")
    assert "set" in run(runner, book, "setting", "list").output


def test_a_value_that_is_not_a_number_is_refused(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "setting", "set", "lmc.tolerance", "plenty")
    assert result.exception is not None


def test_a_setting_nobody_defined_is_refused(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    result = run(runner, book, "setting", "get", "weight.of.the.world")
    assert result.exception is not None


def test_a_setting_can_go_back_to_its_default(runner: CliRunner, book: Path) -> None:
    run(runner, book, "init")
    run(runner, book, "setting", "set", "lmc.tolerance", "300")
    result = run(runner, book, "setting", "clear", "lmc.tolerance")
    assert "is back to 500" in result.output


def test_the_group_is_registered_under_its_name() -> None:
    assert cli.commands["setting"] is policy.group
