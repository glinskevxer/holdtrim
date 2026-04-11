"""The README describes this package and not a previous one.

Two things in a README go stale without anybody noticing: a command that has
been renamed, and a path that has been moved. Both are quoted in the README as
if they were true, and both are checkable.

Prose is not checked and should not be. This looks only at the indented blocks,
which is where the commands and the paths are.
"""

from __future__ import annotations

import shlex
import sys

from holdtrim.tools.check_workflow import resolve
from holdtrim.tools.sources import ROOT, report

README = ROOT / "README.md"
CONSOLE_SCRIPT = "holdtrim"
INDENT = "    "


def blocks(text: str) -> list[str]:
    """Every indented line of the README, continuations joined."""
    found = []
    building = ""
    for raw in text.splitlines():
        if not raw.startswith(INDENT):
            continue
        line = raw.strip()
        if building:
            building = f"{building} {line.rstrip('\\').strip()}"
            if not line.endswith("\\"):
                found.append(building)
                building = ""
            continue
        if line.endswith("\\"):
            building = line.rstrip("\\").strip()
        else:
            found.append(line)
    return found


def commands(text: str) -> list[str]:
    """Every console script invocation the README shows."""
    return [line for line in blocks(text) if line.startswith(f"{CONSOLE_SCRIPT} ")]


def paths(text: str) -> list[str]:
    """Every path the README claims exists."""
    found = []
    for line in blocks(text):
        first = line.split()[0] if line.split() else ""
        if "/" in first and not first.startswith("-") and not first.endswith(".sqlite3"):
            found.append(first)
    return found


def problems() -> list[str]:
    """Every command or path the README names that is not there."""
    if not README.exists():
        return [f"there is no README at {README}"]
    text = README.read_text(encoding="utf-8")
    found = []
    for line in commands(text):
        _path, missing = resolve(shlex.split(line)[1:])
        if missing:
            found.append(f"the README shows {line!r} and {missing!r} is not a command")
    for path in paths(text):
        if not (ROOT / path).exists():
            found.append(f"the README names {path}, which is not there")
    return found


def main() -> int:
    """Run the check and report."""
    text = README.read_text(encoding="utf-8") if README.exists() else ""
    return report(problems(), checked=len(blocks(text)), what="README lines")


if __name__ == "__main__":
    sys.exit(main())
