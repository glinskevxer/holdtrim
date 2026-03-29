"""A test name is a claim about the code, so it has to say something.

Three rules, all of them learned by writing a name that broke one of them.

Four words at least. A name of three words is nearly always a category rather
than a claim: "the check passes" says which thing ran, not what it should do.

No vague words. "works", "correct", "good" and "handles" all mean the test
author knew what they meant at the time. Nobody reading a failure at six in the
morning does.

And no duplicate names within a file, which pytest allows and which quietly
means only the second one runs.
"""

from __future__ import annotations

import ast
import sys

from holdtrim.tools.sources import parsed, report, test_files, where

LEAST_WORDS = 4
VAGUE = {
    "works",
    "correct",
    "correctly",
    "ok",
    "good",
    "fine",
    "stuff",
    "things",
    "handles",
    "behaves",
    "properly",
}


def words(name: str) -> list[str]:
    """The words of a test name, the leading test dropped."""
    return [word for word in name.removeprefix("test_").split("_") if word]


def problems() -> list[str]:
    """Every test name that does not read as a claim."""
    found = []
    for path in test_files():
        seen: set[str] = set()
        for node in ast.walk(parsed(path)):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            place = f"{where(path)}:{node.lineno}"
            said = words(node.name)
            if len(said) < LEAST_WORDS:
                found.append(
                    f"{place}: {node.name} is {len(said)} words, a name is a claim "
                    f"and needs at least {LEAST_WORDS}"
                )
            vague = sorted(set(said) & VAGUE)
            if vague:
                found.append(f"{place}: {node.name} says {', '.join(vague)}, which says nothing")
            if node.name in seen:
                found.append(f"{place}: {node.name} is defined twice in this file")
            seen.add(node.name)
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(test_files()), what="test files")


if __name__ == "__main__":
    sys.exit(main())
