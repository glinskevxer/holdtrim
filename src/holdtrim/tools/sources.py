"""Finding the source this package is made of, for the checks to read."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import holdtrim

PACKAGE = Path(holdtrim.__file__).resolve().parent
ROOT = PACKAGE.parent.parent
TESTS = ROOT / "tests"


def package_files() -> list[Path]:
    """Every source file in the package, in a stable order."""
    return sorted(path for path in PACKAGE.rglob("*.py") if "__pycache__" not in path.parts)


def test_files() -> list[Path]:
    """Every test file, in a stable order."""
    if not TESTS.exists():
        return []
    return sorted(path for path in TESTS.rglob("test_*.py") if "__pycache__" not in path.parts)


def module_name(path: Path) -> str:
    """The dotted name a source file is imported under."""
    relative = path.relative_to(PACKAGE.parent).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def where(path: Path) -> str:
    """The path as it is written in a report, relative to the repository."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:  # pragma: no cover - only if the tree is moved
        return str(path)


def parsed(path: Path) -> ast.Module:
    """One source file as a syntax tree."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def definitions(tree: ast.Module) -> Iterator[ast.AST]:
    """Every module level and nested definition in a file."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


def report(problems: list[str], *, checked: int, what: str) -> int:
    """Print what was found and give the exit status the caller should use."""
    for problem in problems:
        print(problem)
    if problems:
        print(f"{len(problems)} problem(s) in {checked} {what}")
        return 1
    print(f"{checked} {what} checked, nothing to report")
    return 0
