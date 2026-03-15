"""The pins in the project file and the constraints agree.

Two files say what this package installs and they can drift. The project file
names the direct dependencies and the constraints file names the whole closure,
transitive dependencies included, so that a build next year installs what a
build today installed.

The check is that every direct pin appears in the constraints at the same
version, that nothing in the constraints is unpinned, and that both are pinned
with == rather than a range. A range in a constraints file is not a constraint.
"""

from __future__ import annotations

import re
import sys
import tomllib

from holdtrim.tools.sources import ROOT, report

PROJECT = ROOT / "pyproject.toml"
CONSTRAINTS = ROOT / "constraints.txt"

_PIN = re.compile(r"^([A-Za-z0-9_.\-]+)==([A-Za-z0-9_.\-]+)$")


def direct() -> dict[str, str]:
    """The direct dependencies, development ones included."""
    parsed = tomllib.loads(PROJECT.read_text(encoding="utf-8"))
    project = parsed.get("project", {})
    wanted = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        wanted.extend(group)
    pinned = {}
    for entry in wanted:
        match = _PIN.match(entry.strip())
        if match:
            pinned[match.group(1).lower().replace("_", "-")] = match.group(2)
    return pinned


def constrained() -> dict[str, str]:
    """Everything the constraints file pins."""
    pinned = {}
    for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _PIN.match(stripped)
        if match:
            pinned[match.group(1).lower().replace("_", "-")] = match.group(2)
    return pinned


def unpinned() -> list[str]:
    """Every line of the constraints file that is not an exact pin."""
    loose = []
    for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not _PIN.match(stripped):
            loose.append(stripped)
    return loose


def problems() -> list[str]:
    """Everything the two files disagree about."""
    found = [f"constraints.txt does not pin {line!r} exactly" for line in unpinned()]
    held = constrained()
    for name, version in sorted(direct().items()):
        if name not in held:
            found.append(f"{name} is a dependency and constraints.txt does not carry it")
        elif held[name] != version:
            found.append(
                f"{name} is pinned to {version} in pyproject.toml and "
                f"{held[name]} in constraints.txt"
            )
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(constrained()), what="pins")


if __name__ == "__main__":
    sys.exit(main())
