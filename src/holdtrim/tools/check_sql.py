"""Values reach sqlite as parameters, never as text in the statement.

Every value this package writes goes in as a bound parameter. That is not only
about injection, although a station code typed by a handling agent is exactly
the sort of thing that eventually contains a quote. It is also about types: a
Decimal formatted into a statement becomes whatever str gives, and a bound one
goes in as the text the store decided on.

Statements are allowed to be built from fixed fragments, because the column
lists are long and repeating them is worse. A fragment has to be a constant
that is named in capitals, or a join of one, so that whatever ends up in the
statement was written in this repository rather than passed in at runtime.

There is one more thing allowed and it exists for exactly one reason. A PRAGMA
cannot take a bound parameter, so setting the busy timeout means putting a
number in the text. An interpolation wrapped in ``int()`` is accepted, because
whatever went in, what comes out is a number.
"""

from __future__ import annotations

import ast
import sys

from holdtrim.tools.sources import package_files, parsed, report, where

EXECUTE = {"execute", "executemany", "executescript"}


def _is_fragment(node: ast.expr) -> bool:
    """Whether an interpolation is a fixed fragment rather than a value."""
    if isinstance(node, ast.Name):
        return node.id.isupper()
    if isinstance(node, ast.Attribute):
        return node.attr.isupper()
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr == "join"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id == "int"
    return False


def _statement_problems(node: ast.Call, path_name: str) -> list[str]:
    found = []
    statement = node.args[0]
    line = node.lineno
    if isinstance(statement, ast.JoinedStr):
        for part in statement.values:
            if isinstance(part, ast.FormattedValue) and not _is_fragment(part.value):
                found.append(
                    f"{path_name}:{line}: a value is formatted into the statement, "
                    "bind it as a parameter instead"
                )
    elif isinstance(statement, ast.BinOp) and isinstance(statement.op, ast.Mod | ast.Add):
        found.append(
            f"{path_name}:{line}: the statement is built by concatenation, "
            "bind the value as a parameter instead"
        )
    return found


def problems() -> list[str]:
    """Every statement with a value formatted into it."""
    found: list[str] = []
    for path in package_files():
        for node in ast.walk(parsed(path)):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr not in EXECUTE:
                continue
            found.extend(_statement_problems(node, where(path)))
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(package_files()), what="source files")


if __name__ == "__main__":
    sys.exit(main())
