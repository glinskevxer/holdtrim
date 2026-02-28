from pathlib import Path

import click
import pytest

from holdtrim.tools import build_docs
from holdtrim.tools.build_docs import render, usage


def test_the_written_reference_is_current() -> None:
    assert build_docs.main(["--check"]) == 0


def test_the_reference_names_every_group() -> None:
    text = render()
    assert "## `holdtrim station`" in text
    assert "## `holdtrim danger`" in text


def test_the_reference_names_a_command_and_its_options() -> None:
    text = render()
    assert "### `holdtrim station add`" in text
    assert "`--elevation`" in text


def test_a_command_section_lists_its_arguments() -> None:
    @click.command()
    @click.argument("code")
    @click.option("--loud", help="How loud.")
    def shout(code: str, loud: str) -> None:
        """Shout at somebody."""

    lines = usage("cli shout", shout)
    assert lines[0] == "### `holdtrim shout`"
    assert "Arguments: `code`" in lines
    assert any("--loud" in line for line in lines)


def test_a_command_with_no_options_prints_no_table() -> None:
    @click.command()
    def quiet() -> None:
        """Say nothing."""

    assert not any("| option |" in line for line in usage("cli quiet", quiet))


def test_writing_the_reference_puts_it_where_asked(tmp_path: Path) -> None:
    out = tmp_path / "deep" / "commands.md"
    assert build_docs.main(["--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == render()


def test_a_reference_that_was_never_written_fails_the_check(tmp_path: Path) -> None:
    assert build_docs.main(["--check", "--out", str(tmp_path / "nothing.md")]) == 1


def test_a_stale_reference_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "commands.md"
    out.write_text("out of date", encoding="utf-8")
    assert build_docs.main(["--check", "--out", str(out)]) == 1
    assert "out of date" in capsys.readouterr().out
