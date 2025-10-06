"""Every module, class and public function says what it is for.

A docstring on anything the rest of the package calls is not optional. A
private helper is exempt, and so is anything named with a dunder, because
``__post_init__`` and ``__str__`` already say what they are and a line
repeating that is noise the next reader has to skip.

The rule is not about documentation for its own sake. A function nobody can
describe in one line is usually a function doing two things.
"""

from __future__ import annotations

import ast
import sys

from holdtrim.tools.sources import definitions, package_files, parsed, report, where


def problems() -> list[str]:
    """Everything without a docstring that should have one."""
    found = []
    for path in package_files():
        tree = parsed(path)
        if ast.get_docstring(tree) is None:
            found.append(f"{where(path)}: the module has no docstring")
        for node in definitions(tree):
            name = getattr(node, "name", "")
            if name.startswith("_"):
                continue
            if ast.get_docstring(node) is None:  # type: ignore[arg-type]
                line = getattr(node, "lineno", 0)
                found.append(f"{where(path)}:{line}: {name} has no docstring")
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(package_files()), what="source files")


if __name__ == "__main__":
    sys.exit(main())
