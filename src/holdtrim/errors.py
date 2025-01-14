"""Every error this package raises on purpose.

Each one carries a short stable ``code``. The CLI turns the code into an exit
status and the reports quote it, so codes are part of the interface and are
not renamed once used.
"""

from __future__ import annotations


class HoldtrimError(Exception):
    """Base class for everything raised deliberately."""

    code = "holdtrim"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class DataError(HoldtrimError):
    """Input that cannot be read as what it claims to be."""

    code = "data"


class UnitError(DataError):
    """A weight, length or index that is not a usable quantity."""

    code = "unit"


class IdentifierError(DataError):
    """An identifier that fails the format or the check digit."""

    code = "identifier"


class NotFoundError(HoldtrimError):
    """A record that was asked for by identifier and is not in the book."""

    code = "not-found"


class DuplicateError(HoldtrimError):
    """A record that already exists under that identifier."""

    code = "duplicate"


class StateError(HoldtrimError):
    """The record exists but is in the wrong state for what was asked."""

    code = "state"


class RuleError(HoldtrimError):
    """A load control rule says no."""

    code = "rule"


class LimitError(RuleError):
    """A certified or structural limit has been passed."""

    code = "limit"

    def __init__(self, message: str, *, limit: int, actual: int) -> None:
        super().__init__(message)
        self.limit = limit
        self.actual = actual

    @property
    def over_by(self) -> int:
        """How far past the limit the figure sits, never negative."""
        return max(0, self.actual - self.limit)


class BookError(HoldtrimError):
    """The store itself cannot serve the request."""

    code = "book"
