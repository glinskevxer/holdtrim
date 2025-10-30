"""Every module is reached by at least one test.

This is a coverage question asked the other way round. Line coverage tells you
which lines ran; it does not tell you that anybody wrote a test about a module,
because a module can be exercised entirely by accident through something else
that imports it.

So the check is about intent: somewhere under tests there is a file that names
this module. It is a low bar and it is worth having, because the module that
nothing names is nearly always the one nobody thought about.
"""

from __future__ import annotations

import ast
import sys

from holdtrim.tools.sources import module_name, package_files, parsed, report, test_files, where

EXEMPT = {"holdtrim"}


def named_in_tests() -> set[str]:
    """Every holdtrim module a test file imports, however it imports it.

    ``from holdtrim.store import fleet`` names ``holdtrim.store.fleet`` as
    surely as importing it by its full name does, so both forms are read out
    of the syntax tree rather than matched in the text.
    """
    named: set[str] = set()
    for path in test_files():
        for node in ast.walk(parsed(path)):
            if isinstance(node, ast.Import):
                named.update(
                    alias.name for alias in node.names if alias.name.startswith("holdtrim")
                )
            elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("holdtrim"):
                module = str(node.module)
                named.add(module)
                named.update(f"{module}.{alias.name}" for alias in node.names)
    return named


def problems() -> list[str]:
    """Every module no test file imports."""
    named = named_in_tests()
    found = []
    for path in package_files():
        if path.name == "__init__.py":
            continue
        name = module_name(path)
        if name in EXEMPT or name in named:
            continue
        found.append(f"{where(path)}: {name} is not named by any test")
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(package_files()), what="source files")


if __name__ == "__main__":
    sys.exit(main())
