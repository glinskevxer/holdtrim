"""The commands in the CI walk are commands this tool actually has.

The walk job runs a whole shift through the console script, which is the only
place the commands are exercised together. It is also a shell script inside a
YAML file, so nothing checks it until it runs, and when it breaks it breaks in
CI on somebody else's pull request.

This reads the walk out of the workflow, joins the line continuations, and
resolves every command against the command tree. It does not run anything: it
answers whether the words are words this tool knows, which is what actually
goes wrong when a command is renamed.
"""

from __future__ import annotations

import re
import shlex
import sys

import click

from holdtrim.cli.main import cli
from holdtrim.tools.sources import ROOT, report

WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
CONSOLE_SCRIPT = "holdtrim"

_CONTINUED = re.compile(r"\\\s*$")


def invocations(text: str) -> list[str]:
    """Every console script invocation in the workflow, continuations joined."""
    found = []
    building = ""
    for raw in text.splitlines():
        line = raw.strip()
        if building:
            building = f"{building} {_CONTINUED.sub('', line).strip()}"
            if not _CONTINUED.search(line):
                found.append(building.strip())
                building = ""
            continue
        if not line.startswith(f"{CONSOLE_SCRIPT} "):
            continue
        if _CONTINUED.search(line):
            building = _CONTINUED.sub("", line).strip()
        else:
            found.append(line)
    return found


def resolve(words: list[str]) -> tuple[list[click.Command], str]:
    """Walk the command tree with the words of an invocation.

    Options are skipped as they are met, and so is the word after one unless
    that word is itself an option. That is a guess, and it is the right guess
    here because every option this tool has that takes no value is a flag on a
    leaf command rather than on a group.
    """
    path: list[click.Command] = [cli]
    index = 0
    while index < len(words):
        word = words[index]
        if word.startswith("-"):
            index += 1
            if index < len(words) and not words[index].startswith("-"):
                index += 1
            continue
        current = path[-1]
        if not isinstance(current, click.Group):
            break
        found = current.commands.get(word)
        if found is None:
            return path, word
        path.append(found)
        index += 1
    return path, ""


def option_names(command: click.Command) -> set[str]:
    """Every option flag a command accepts."""
    names: set[str] = set()
    for parameter in command.params:
        if isinstance(parameter, click.Option):
            names.update(parameter.opts)
            names.update(parameter.secondary_opts)
    return names


def walk_text() -> str:
    """The workflow as text, empty when there is not one."""
    if not WORKFLOW.exists():
        return ""
    return WORKFLOW.read_text(encoding="utf-8")


def problems(text: str | None = None) -> list[str]:
    """Every invocation the command tree cannot answer."""
    if text is None:
        if not WORKFLOW.exists():
            return [f"there is no workflow at {WORKFLOW}"]
        text = walk_text()
    found = []
    for line in invocations(text):
        words = shlex.split(line)[1:]
        path, missing = resolve(words)
        if missing:
            found.append(f"{line!r} names {missing!r}, which is not a command")
            continue
        allowed: set[str] = set()
        for command in path:
            allowed |= option_names(command)
        for word in words:
            if word.startswith("-") and word not in allowed:
                found.append(f"{line!r} passes {word}, which that command does not take")
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(invocations(walk_text())), what="walk commands")


if __name__ == "__main__":
    sys.exit(main())
