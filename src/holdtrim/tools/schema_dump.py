"""The schema as one file, so a change to it is visible in a diff.

Migrations are the truth and they are also unreadable as a whole: the shape of
the station table after eleven of them is not something anybody can hold in
their head. This writes the shape out, and CI checks it is current, so a review
of a migration comes with a review of what the book will look like afterwards.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from holdtrim.store.migrations import MIGRATIONS, apply
from holdtrim.store.sqlite import opened, rows
from holdtrim.tools.sources import ROOT

DOCUMENT = ROOT / "docs" / "schema.sql"


def render() -> str:
    """Every table and index in the book, in name order."""
    lines = [
        "-- The shape of the book after every migration.",
        f"-- Written by python -m holdtrim.tools.schema_dump at schema {MIGRATIONS[-1].version}.",
        "",
    ]
    with (
        tempfile.TemporaryDirectory() as where,
        opened(Path(where) / "schema.sqlite3") as connection,
    ):
        apply(connection)
        found = rows(
            connection,
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
            "ORDER BY type, name",
        )
        for row in found:
            statement = " ".join(str(row["sql"]).split())
            lines.append(f"{statement};")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the schema out, or check that the written one is current."""
    parser = argparse.ArgumentParser(description="Dump the schema of the book.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path, default=DOCUMENT)
    arguments = parser.parse_args(argv)
    wanted = render()
    if arguments.check:
        if not arguments.out.exists():
            print(f"{arguments.out} has never been written")
            return 1
        if arguments.out.read_text(encoding="utf-8") != wanted:
            print(f"{arguments.out} is out of date, run python -m holdtrim.tools.schema_dump")
            return 1
        print(f"{arguments.out} is current")
        return 0
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(wanted, encoding="utf-8")
    print(f"wrote {arguments.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
