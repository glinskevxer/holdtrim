"""A finding: one thing wrong, said the same way wherever it was found.

Weight and balance, dangerous goods screening and the loadsheet checks all
produce the same shape of answer, and a load controller reads them in one list.
They used to each have their own little record with the same three fields and
slightly different names, which meant the printing code had to know which was
which. It does not any more.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

STOP = "stop"
WATCH = "watch"
SEVERITIES = (STOP, WATCH)


@dataclass(frozen=True)
class Finding:
    """One thing wrong, where it is, and by how much."""

    check: str
    where: str
    detail: str
    over_by: int = 0
    severity: str = STOP

    @property
    def stops_the_flight(self) -> bool:
        """Whether this one has to be fixed before the aeroplane goes."""
        return self.severity == STOP

    def describe(self) -> str:
        """One line for the load controller."""
        return f"{self.check} {self.where}: {self.detail}"


def stopping(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    """The findings that have to be fixed, in the order they were found."""
    return tuple(finding for finding in findings if finding.stops_the_flight)


def watching(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    """The findings worth knowing about that do not stop anything."""
    return tuple(finding for finding in findings if not finding.stops_the_flight)


def by_check(findings: Iterable[Finding]) -> dict[str, tuple[Finding, ...]]:
    """The findings grouped by which check produced them."""
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.check, []).append(finding)
    return {check: tuple(found) for check, found in sorted(grouped.items())}


def worst(findings: Iterable[Finding]) -> Finding | None:
    """The finding that is over by the most, or nothing when all is well."""
    listed = list(findings)
    if not listed:
        return None
    return max(listed, key=lambda finding: (finding.stops_the_flight, finding.over_by))


def lines(findings: Iterable[Finding]) -> tuple[str, ...]:
    """Every finding as a line, for a report or a terminal."""
    return tuple(finding.describe() for finding in findings)
