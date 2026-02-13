"""Every module is reachable from something that runs.

A module with tests and no caller is tested and not used, and the two are easy
to confuse when the test suite is green. It happens most often after a piece of
work stops halfway: the dangerous goods screening was written, tested and left
with nothing calling it for a month, and the suite stayed green the whole time.

The check walks the import graph out from the console script and from the
checks CI runs, and reports anything it never reaches.
"""

from __future__ import annotations

import ast
import sys

from holdtrim.tools.sources import PACKAGE, module_name, package_files, parsed, report, where

ENTRY_POINTS = ("holdtrim.cli.main",)


def edges() -> dict[str, set[str]]:
    """Which module imports which, across the whole package."""
    graph: dict[str, set[str]] = {}
    for path in package_files():
        name = module_name(path)
        imported: set[str] = set()
        for node in ast.walk(parsed(path)):
            if isinstance(node, ast.Import):
                imported.update(
                    alias.name for alias in node.names if alias.name.startswith("holdtrim")
                )
            elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("holdtrim"):
                module = str(node.module)
                imported.add(module)
                imported.update(f"{module}.{alias.name}" for alias in node.names)
        graph[name] = imported
    return graph


def reachable(graph: dict[str, set[str]], roots: tuple[str, ...]) -> set[str]:
    """Every module reachable from the roots, roots included."""
    seen: set[str] = set()
    waiting = list(roots)
    while waiting:
        here = waiting.pop()
        if here in seen:
            continue
        seen.add(here)
        waiting.extend(name for name in graph.get(here, set()) if name not in seen)
    return seen


def roots() -> tuple[str, ...]:
    """The entry points, and the checks CI runs directly."""
    checks = tuple(
        module_name(path)
        for path in sorted((PACKAGE / "tools").glob("*.py"))
        if path.name != "__init__.py"
    )
    return (*ENTRY_POINTS, *checks)


def problems() -> list[str]:
    """Every module nothing that runs can reach."""
    graph = edges()
    seen = reachable(graph, roots())
    found = []
    for path in package_files():
        if path.name == "__init__.py":
            continue
        name = module_name(path)
        if name not in seen:
            found.append(f"{where(path)}: {name} is not reached from anything that runs")
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(package_files()), what="source files")


if __name__ == "__main__":
    sys.exit(main())
