"""The design note describes this package and every part of it.

Two ways a design note goes wrong. It names a module that has been renamed, and
it quietly stops mentioning a package that was added after it was written. The
second is the one that matters: a new top level package is exactly the thing a
reader needs the note to explain, and it is exactly the thing nobody remembers
to add.

So the check runs both ways. Everything the note names has to exist, and every
package has to be named.
"""

from __future__ import annotations

import re
import sys

from holdtrim.tools.sources import PACKAGE, ROOT, report

DESIGN = ROOT / "DESIGN.md"

_MODULE = re.compile(r"holdtrim(?:\.[a-z_]+)+")


def named(text: str) -> list[str]:
    """Every holdtrim module the note names, once each."""
    return sorted(set(_MODULE.findall(text)))


def packages() -> list[str]:
    """Every top level package under holdtrim."""
    return sorted(
        f"holdtrim.{path.name}"
        for path in PACKAGE.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    )


def exists(module: str) -> bool:
    """Whether a named module is really there."""
    parts = module.split(".")[1:]
    here = PACKAGE.joinpath(*parts)
    return here.with_suffix(".py").exists() or (here / "__init__.py").exists()


def problems() -> list[str]:
    """Everything the note names that is gone, and every package it leaves out."""
    if not DESIGN.exists():
        return [f"there is no design note at {DESIGN}"]
    text = DESIGN.read_text(encoding="utf-8")
    mentioned = named(text)
    found = [
        f"the design note names {module}, which is not there"
        for module in mentioned
        if not exists(module)
    ]
    found.extend(
        f"{package} is a package and the design note never mentions it"
        for package in packages()
        if package not in mentioned
    )
    return found


def main() -> int:
    """Run the check and report."""
    text = DESIGN.read_text(encoding="utf-8") if DESIGN.exists() else ""
    return report(problems(), checked=len(named(text)), what="modules the note names")


if __name__ == "__main__":
    sys.exit(main())
