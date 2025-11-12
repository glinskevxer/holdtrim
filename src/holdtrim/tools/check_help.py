"""Every command and every option says what it does.

The command line is the whole interface. Somebody working a night shift finds
out what this tool can do by typing --help, and an option with no help text is
an option they will not use or, worse, will guess at.

The check also refuses a help line that does not end in a full stop and one
that starts in lower case, not out of fussiness but because the help output is
a wall of short lines and inconsistent ones are hard to scan.
"""

from __future__ import annotations

import sys

import click

from holdtrim.cli.main import cli
from holdtrim.tools.sources import report

SKIPPED_OPTIONS = {"help", "version"}


def walk(command: click.Command, path: str = "") -> list[tuple[str, click.Command]]:
    """Every command in the tree, with the words that reach it."""
    here = f"{path} {command.name}".strip()
    found = [(here, command)]
    if isinstance(command, click.Group):
        for name in sorted(command.commands):
            found.extend(walk(command.commands[name], here))
    return found


def problems() -> list[str]:
    """Every command or option that does not explain itself."""
    found = []
    for name, command in walk(cli):
        if not (command.help or "").strip():
            found.append(f"{name}: the command has no help text")
        for parameter in command.params:
            if not isinstance(parameter, click.Option):
                continue
            if parameter.name in SKIPPED_OPTIONS:
                continue
            text = (parameter.help or "").strip()
            if not text:
                found.append(f"{name}: --{parameter.name} has no help text")
                continue
            if not text.endswith("."):
                found.append(f"{name}: --{parameter.name} help does not end in a full stop")
            if text[:1].islower():
                found.append(f"{name}: --{parameter.name} help starts in lower case")
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(walk(cli)), what="commands")


if __name__ == "__main__":
    sys.exit(main())
