"""Every check runs in CI and has a test of its own.

A check that is written and not wired into CI is a check that passes forever.
It happened here with the wiring check, which sat for two commits doing nothing
while the thing it was written to catch was in the tree.

So this is the check on the checks. Each module under tools has to have a main
that CI can call, has to be named in the lint job, and has to have a test file.
The last one matters more than it sounds: a check with no test is a check
nobody has seen fire, and a check nobody has seen fire is not a check.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from holdtrim.tools.sources import PACKAGE, TESTS, report

TOOLS = PACKAGE / "tools"
WORKFLOW = PACKAGE.parent.parent / ".github" / "workflows" / "ci.yml"
NOT_A_CHECK = {"sources", "smoke", "coverage_gate"}
NOT_RUNNABLE = {"sources"}


def tool_names() -> list[str]:
    """Every module under tools, in name order."""
    return sorted(path.stem for path in TOOLS.glob("*.py") if path.stem not in {"__init__"})


def runnable(name: str) -> bool:
    """Whether the module has a main CI can call."""
    module = importlib.import_module(f"holdtrim.tools.{name}")
    return callable(getattr(module, "main", None))


def named_in_workflow(text: str, name: str) -> bool:
    """Whether the workflow runs this module."""
    return f"holdtrim.tools.{name}" in text


def expected_test(name: str) -> Path:
    """Where the test for a tool has to be."""
    return TESTS / "tools" / f"test_{name}.py"


def problems() -> list[str]:
    """Every tool that is not runnable, not run, or not tested."""
    text = WORKFLOW.read_text(encoding="utf-8") if WORKFLOW.exists() else ""
    found = []
    for name in tool_names():
        if name not in NOT_RUNNABLE and not runnable(name):
            found.append(f"holdtrim.tools.{name} has no main for CI to call")
        if name not in NOT_A_CHECK and not named_in_workflow(text, name):
            found.append(f"holdtrim.tools.{name} is never run by the workflow")
        if not expected_test(name).exists():
            found.append(f"holdtrim.tools.{name} has no test file at {expected_test(name).name}")
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(tool_names()), what="tools")


if __name__ == "__main__":
    sys.exit(main())
