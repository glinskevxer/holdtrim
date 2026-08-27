"""The package would install as the thing it says it is.

Three small things that only go wrong at release, and each of which is
invisible until somebody installs the wheel.

The typing marker has to be in the package, or every type this repository is
so careful about is thrown away the moment it is imported by somebody else.
The wheel has to be told which directory to take. And the console script has to
point at a function that is really there under that name.
"""

from __future__ import annotations

import importlib
import sys
import tomllib

from holdtrim.tools.sources import PACKAGE, ROOT, report

PROJECT = ROOT / "pyproject.toml"
MARKER = PACKAGE / "py.typed"


def project() -> dict[str, object]:
    """The project file, parsed."""
    parsed: dict[str, object] = tomllib.loads(PROJECT.read_text(encoding="utf-8"))
    return parsed


def wheel_packages() -> list[str]:
    """The directories the wheel is told to take."""
    parsed = project()
    tool = parsed.get("tool", {})
    if not isinstance(tool, dict):
        return []
    hatch = tool.get("hatch", {})
    build = hatch.get("build", {}) if isinstance(hatch, dict) else {}
    targets = build.get("targets", {}) if isinstance(build, dict) else {}
    wheel = targets.get("wheel", {}) if isinstance(targets, dict) else {}
    listed = wheel.get("packages", []) if isinstance(wheel, dict) else []
    return [str(entry) for entry in listed]


def scripts() -> dict[str, str]:
    """The console scripts the project declares."""
    parsed = project()
    section = parsed.get("project", {})
    if not isinstance(section, dict):
        return {}
    declared = section.get("scripts", {})
    return {str(name): str(target) for name, target in declared.items()}


def points_at_something(target: str) -> bool:
    """Whether a console script target really exists."""
    module, _, attribute = target.partition(":")
    try:
        imported = importlib.import_module(module)
    except ModuleNotFoundError:
        return False
    return callable(getattr(imported, attribute, None))


def problems() -> list[str]:
    """Everything that would go wrong at install time."""
    found = []
    if not MARKER.exists():
        found.append("there is no py.typed in the package, the types will be thrown away")
    packages = wheel_packages()
    if "src/holdtrim" not in packages:
        found.append(f"the wheel is told to take {packages}, which does not include src/holdtrim")
    declared = scripts()
    if not declared:
        found.append("the project declares no console script")
    for name, target in sorted(declared.items()):
        if not points_at_something(target):
            found.append(f"the {name} script points at {target}, which is not there")
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(scripts()) + 2, what="packaging facts")


if __name__ == "__main__":
    sys.exit(main())
