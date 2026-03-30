"""A fixture that opens a book closes it.

A sqlite connection left open by a fixture is not a leak anybody notices on
3.12. On 3.13 it raises a ResourceWarning when the garbage collector gets to
it, filterwarnings turns that into an error, and the error is attributed to
whichever test the collector happened to interrupt. The failure moves around
between runs and points at innocent tests.

The rule that avoids all of it: a fixture that opens anything yields from
inside a with block. This reads the fixtures rather than trusting anybody to
remember, because the trusting version is how the problem got here.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from holdtrim.tools.sources import TESTS, parsed, report, test_files, where

OPENERS = {"opened", "connect", "open_book", "initialise"}


def is_fixture(node: ast.FunctionDef) -> bool:
    """Whether a function is decorated as a pytest fixture."""
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Attribute) and target.attr == "fixture":
            return True
        if isinstance(target, ast.Name) and target.id == "fixture":
            return True
    return False


def opens(node: ast.FunctionDef) -> bool:
    """Whether the fixture body opens something that has to be closed."""
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call):
            continue
        called = inner.func
        if isinstance(called, ast.Name) and called.id in OPENERS:
            return True
        if isinstance(called, ast.Attribute) and called.attr in OPENERS:
            return True
    return False


def yields_outside_with(node: ast.FunctionDef) -> bool:
    """Whether the fixture yields from somewhere other than inside a with."""
    inside: set[int] = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.With | ast.AsyncWith):
            for held in ast.walk(inner):
                if isinstance(held, ast.Yield):
                    inside.add(id(held))
    return any(isinstance(inner, ast.Yield) and id(inner) not in inside for inner in ast.walk(node))


def fixture_files() -> list[Path]:
    """Every test file and every conftest, which is where fixtures live."""
    found = list(test_files())
    if TESTS.exists():
        found.extend(
            path for path in sorted(TESTS.rglob("conftest.py")) if "__pycache__" not in path.parts
        )
    return found


def problems() -> list[str]:
    """Every fixture that opens something and does not close it."""
    found = []
    for path in fixture_files():
        for node in ast.walk(parsed(path)):
            if not isinstance(node, ast.FunctionDef) or not is_fixture(node):
                continue
            if opens(node) and yields_outside_with(node):
                found.append(
                    f"{where(path)}:{node.lineno}: the fixture {node.name} opens something "
                    "and yields from outside a with block"
                )
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(fixture_files()), what="files with fixtures")


if __name__ == "__main__":
    sys.exit(main())
