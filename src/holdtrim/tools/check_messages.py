"""Error messages read the same way wherever they come from.

The command line prints "error: " and then the message, so a message that
starts with a capital or ends with a full stop reads as a fragment of somebody
else's sentence. They also get quoted inside longer lines in reports, where a
stray full stop in the middle is worse.

Three rules, and they are the ones that were actually being broken.

No trailing full stop. No leading capital, unless the first word is something
that is capitalised anyway, like UN or a station code. And no message that
starts by saying "error", because the caller has already said that.
"""

from __future__ import annotations

import ast
import sys

from holdtrim.tools.sources import package_files, parsed, report, where

ERRORS = {
    "HoldtrimError",
    "DataError",
    "UnitError",
    "IdentifierError",
    "NotFoundError",
    "DuplicateError",
    "StateError",
    "RuleError",
    "LimitError",
    "BookError",
}
FORBIDDEN_OPENINGS = ("error", "exception", "failed")


def opening(node: ast.expr) -> str:
    """The literal text a message starts with, empty when it starts with a value."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and node.values:
        first = node.values[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    return ""


def ending(node: ast.expr) -> str:
    """The literal text a message ends with, empty when it ends with a value."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and node.values:
        last = node.values[-1]
        if isinstance(last, ast.Constant) and isinstance(last.value, str):
            return last.value
    return ""


def _problems_for(node: ast.Call, place: str) -> list[str]:
    found = []
    start = opening(node.args[0])
    finish = ending(node.args[0])
    if finish.rstrip().endswith("."):
        found.append(f"{place}: the message ends in a full stop")
    first = start.split()[0] if start.split() else ""
    if first and first[0].isupper() and not first.isupper():
        found.append(f"{place}: the message starts with a capital, {first!r}")
    if first.lower().strip(":") in FORBIDDEN_OPENINGS:
        found.append(f"{place}: the message starts by saying {first!r}")
    return found


def problems() -> list[str]:
    """Every message that does not read the way the others do."""
    found = []
    for path in package_files():
        for node in ast.walk(parsed(path)):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if not isinstance(node.func, ast.Name) or node.func.id not in ERRORS:
                continue
            found.extend(_problems_for(node, f"{where(path)}:{node.lineno}"))
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(package_files()), what="source files")


if __name__ == "__main__":
    sys.exit(main())
