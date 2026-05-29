"""A migration that has run anywhere is never edited again.

Editing a migration is the one change to this package that cannot be undone by
another commit. The book on somebody's laptop has already run the old version,
nothing will run the new one, and the two books diverge quietly from then on.

The fingerprint file records what each migration was when it was accepted.
Changing a migration changes its fingerprint and this check fails, which is the
point. Adding one adds a line, and that is the only edit to the file anybody
should ever make.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from holdtrim.store.migrations import MIGRATIONS
from holdtrim.tools.sources import ROOT, report

FINGERPRINTS = ROOT / "docs" / "migrations.txt"


def fingerprint(version: int) -> str:
    """A stable digest of one migration's name and statements."""
    migration = next(entry for entry in MIGRATIONS if entry.version == version)
    text = migration.name + "\n" + "\n".join(" ".join(s.split()) for s in migration.statements)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def current() -> dict[int, str]:
    """What every migration fingerprints to right now."""
    return {migration.version: fingerprint(migration.version) for migration in MIGRATIONS}


def recorded() -> dict[int, str]:
    """What the fingerprint file says they were."""
    if not FINGERPRINTS.exists():
        return {}
    held = {}
    for line in FINGERPRINTS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        version, _, digest = stripped.partition(" ")
        held[int(version)] = digest.strip()
    return held


def render() -> str:
    """The fingerprint file as it should be."""
    lines = [
        "# What each migration was when it was accepted.",
        "# Written by python -m holdtrim.tools.check_migrations --write.",
        "# A changed line here means a migration was edited, which is never right.",
    ]
    lines.extend(f"{version} {digest}" for version, digest in sorted(current().items()))
    return "\n".join(lines) + "\n"


def problems() -> list[str]:
    """Every migration that has changed since it was accepted."""
    held = recorded()
    if not held:
        return ["no migration fingerprints have ever been written"]
    found = []
    for version, digest in sorted(current().items()):
        if version not in held:
            found.append(f"migration {version} has no fingerprint, write one")
        elif held[version] != digest:
            found.append(f"migration {version} has been edited since it was accepted")
    for version in sorted(set(held) - set(current())):
        found.append(f"migration {version} has a fingerprint and is not in the list any more")
    return found


def main(argv: list[str] | None = None) -> int:
    """Check the fingerprints, or write them."""
    parser = argparse.ArgumentParser(description="Check the migrations are unedited.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out", type=Path, default=FINGERPRINTS)
    arguments = parser.parse_args(argv)
    if arguments.write:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(render(), encoding="utf-8")
        print(f"wrote {arguments.out}")
        return 0
    return report(problems(), checked=len(MIGRATIONS), what="migrations")


if __name__ == "__main__":
    sys.exit(main())
