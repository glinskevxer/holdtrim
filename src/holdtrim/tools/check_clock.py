"""Nothing in this package reads the wall clock.

Every date this tool works with is a date somebody gave it: the day of the
flight, the day of the weighing, the day the storage clock started. None of
them is today, and the office is often working a flight that leaves tomorrow
or reconciling one that left last week.

Reading the clock also makes a test that passes in the morning and fails at
midnight, and that kind of test is only found by the person on shift when it
happens.

So the rule is absolute: a day comes in as an argument or it does not come in
at all. The check reads for the calls that break it rather than trusting
anybody to remember.
"""

from __future__ import annotations

import ast
import sys

from holdtrim.tools.sources import package_files, parsed, report, where

FORBIDDEN = {
    "today": "date.today",
    "now": "datetime.now",
    "utcnow": "datetime.utcnow",
    "utcfromtimestamp": "datetime.utcfromtimestamp",
    "fromtimestamp": "datetime.fromtimestamp",
    "monotonic": "time.monotonic",
    "perf_counter": "time.perf_counter",
    "localtime": "time.localtime",
    "gmtime": "time.gmtime",
}

FORBIDDEN_NAMES = {"time"}
FORBIDDEN_MODULES = {"time"}


def _called_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return ""


def problems() -> list[str]:
    """Every call that would read the clock."""
    found: list[str] = []
    for path in package_files():
        tree = parsed(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.extend(
                    f"{where(path)}:{node.lineno}: imports {alias.name}, "
                    "which is a clock this package does not read"
                    for alias in node.names
                    if alias.name in FORBIDDEN_MODULES
                )
            if not isinstance(node, ast.Call):
                continue
            name = _called_name(node)
            if name in FORBIDDEN:
                found.append(
                    f"{where(path)}:{node.lineno}: calls {FORBIDDEN[name]}, "
                    "and a day has to come in as an argument"
                )
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(package_files()), what="source files")


if __name__ == "__main__":
    sys.exit(main())
