"""The command reference, generated from the commands themselves.

A reference written by hand goes out of date on the first afternoon somebody
adds an option, and the way you find out is that a reader tries the option that
is not there any more. This one is generated, and CI runs it with --check so
that a change to a command and a change to the document land in the same
commit.

Help text is put through cleandoc before it is written. Python 3.13 strips the
common indentation from a docstring and 3.12 does not, so the same command
renders two different documents on the two interpreters and the check fails on
whichever one did not write the file.
"""

from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path

import click

from holdtrim import __version__
from holdtrim.cli.main import cli
from holdtrim.tools.check_help import walk
from holdtrim.tools.sources import ROOT

DOCUMENT = ROOT / "docs" / "commands.md"


def helped(command: click.Command) -> str:
    """A command's help text, indented the same way on every interpreter."""
    return inspect.cleandoc(command.help or "").strip()


def usage(name: str, command: click.Command) -> list[str]:
    """One command as a section of the reference."""
    words = name.replace("cli", "holdtrim", 1)
    lines = [f"### `{words}`", "", helped(command), ""]
    arguments = [p for p in command.params if isinstance(p, click.Argument)]
    options = [
        p
        for p in command.params
        if isinstance(p, click.Option) and p.name not in {"help", "version"}
    ]
    if arguments:
        lines.append("Arguments: " + ", ".join(f"`{p.name}`" for p in arguments))
        lines.append("")
    if options:
        lines.append("| option | what it does |")
        lines.append("| --- | --- |")
        for option in options:
            flags = ", ".join(f"`{flag}`" for flag in option.opts)
            lines.append(f"| {flags} | {(option.help or '').strip()} |")
        lines.append("")
    return lines


def render() -> str:
    """The whole reference."""
    lines = [
        "# holdtrim commands",
        "",
        f"Generated from the command line of holdtrim {__version__}.",
        "Run `python -m holdtrim.tools.build_docs` to write this file again.",
        "",
    ]
    for name, command in walk(cli):
        if isinstance(command, click.Group) and name != "cli":
            lines.extend([f"## `{name.replace('cli', 'holdtrim', 1)}`", "", helped(command), ""])
            continue
        lines.extend(usage(name, command))
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the reference, or check that the written one is current."""
    parser = argparse.ArgumentParser(description="Build the command reference.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path, default=DOCUMENT)
    arguments = parser.parse_args(argv)
    wanted = render()
    if arguments.check:
        if not arguments.out.exists():
            print(f"{arguments.out} has never been written")
            return 1
        if arguments.out.read_text(encoding="utf-8") != wanted:
            print(f"{arguments.out} is out of date, run python -m holdtrim.tools.build_docs")
            return 1
        print(f"{arguments.out} is current")
        return 0
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(wanted, encoding="utf-8")
    print(f"wrote {arguments.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
