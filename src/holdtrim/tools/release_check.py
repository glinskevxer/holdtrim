"""The version says the same thing in all three places.

The version lives in the project file, in the package, and at the top of the
changelog, and a release where those three disagree is a release nobody can
identify afterwards. This is a small check and it has caught a wrong number
every time somebody bumped two of the three.
"""

from __future__ import annotations

import re
import sys
import tomllib

from holdtrim import __version__
from holdtrim.tools.sources import ROOT, report

PROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"

_HEADING = re.compile(r"^## +([0-9][0-9A-Za-z.\-]*)")
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def project_version() -> str:
    """The version the project file declares."""
    parsed = tomllib.loads(PROJECT.read_text(encoding="utf-8"))
    return str(parsed.get("project", {}).get("version", ""))


def changelog_versions() -> list[str]:
    """Every version the changelog has a section for, newest first."""
    found = []
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines():
        match = _HEADING.match(line.strip())
        if match:
            found.append(match.group(1))
    return found


def problems() -> list[str]:
    """Everywhere the three disagree."""
    found = []
    declared = project_version()
    if not _VERSION.match(declared):
        found.append(f"pyproject.toml declares {declared!r}, which is not a version")
    if declared != __version__:
        found.append(f"pyproject.toml says {declared} and the package says {__version__}")
    sections = changelog_versions()
    if not sections:
        found.append("the changelog has no version sections in it")
    elif sections[0] != declared:
        found.append(f"the changelog starts at {sections[0]} and the version is {declared}")
    if len(set(sections)) != len(sections):
        found.append("the changelog has the same version in it twice")
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=3, what="places the version is written")


if __name__ == "__main__":
    sys.exit(main())
