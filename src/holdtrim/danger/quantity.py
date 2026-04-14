"""How much of a thing may be in one package.

The regulations put a limit on the net quantity per package, and the limit is
different on a freighter from what it is on an aeroplane carrying passengers.
That difference is the whole reason cargo aircraft only exists as a category:
the same substance in the same packaging is acceptable in a larger quantity
where there is nobody sitting above it.

The limits here are the operator's extract for the classes this operation
actually accepts. A class that is not in the table is not refused, it is
reported as unlisted, because refusing a shipment on the grounds that a table
in an office system is incomplete is not a decision this code gets to make.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdtrim.findings import STOP, WATCH, Finding
from holdtrim.model.danger import DangerousGoods

QUANTITY = "quantity"
UNLISTED = "unlisted"


@dataclass(frozen=True)
class Allowance:
    """What one package may hold, on a freighter and on a passenger flight."""

    hazard_class: str
    packing_group: str
    unit: str
    passenger_limit: Decimal
    cargo_limit: Decimal

    def limit(self, *, freighter: bool) -> Decimal:
        """The limit that applies on this kind of flight."""
        return self.cargo_limit if freighter else self.passenger_limit

    def describe(self) -> str:
        """One line for the allowance table."""
        group = self.packing_group or "none"
        return (
            f"class {self.hazard_class} packing group {group}: "
            f"{self.passenger_limit} {self.unit} on a passenger flight, "
            f"{self.cargo_limit} {self.unit} on a freighter"
        )


ALLOWANCES: tuple[Allowance, ...] = (
    Allowance("3", "I", "L", Decimal("1"), Decimal("30")),
    Allowance("3", "II", "L", Decimal("5"), Decimal("60")),
    Allowance("3", "III", "L", Decimal("60"), Decimal("220")),
    Allowance("4.1", "II", "kg", Decimal("5"), Decimal("15")),
    Allowance("4.1", "III", "kg", Decimal("10"), Decimal("50")),
    Allowance("5.1", "II", "kg", Decimal("5"), Decimal("25")),
    Allowance("5.1", "III", "kg", Decimal("25"), Decimal("100")),
    Allowance("6.1", "I", "kg", Decimal("0.5"), Decimal("5")),
    Allowance("6.1", "II", "kg", Decimal("5"), Decimal("50")),
    Allowance("6.1", "III", "kg", Decimal("25"), Decimal("100")),
    Allowance("8", "I", "L", Decimal("0.5"), Decimal("2.5")),
    Allowance("8", "II", "L", Decimal("1"), Decimal("30")),
    Allowance("8", "III", "L", Decimal("5"), Decimal("60")),
    Allowance("9", "", "kg", Decimal("200"), Decimal("200")),
)


def allowance_for(entry: DangerousGoods) -> Allowance | None:
    """The allowance for one declared line, or nothing where it is unlisted."""
    for allowance in ALLOWANCES:
        same_class = allowance.hazard_class == entry.hazard_class
        same_group = allowance.packing_group in {entry.packing_group, ""}
        if same_class and same_group:
            return allowance
    return None


def over_by(entry: DangerousGoods, *, freighter: bool) -> Decimal:
    """How much past the per package limit one package is."""
    allowance = allowance_for(entry)
    if allowance is None:
        return Decimal("0")
    return max(Decimal("0"), entry.net_quantity - allowance.limit(freighter=freighter))


def check(
    entries: tuple[DangerousGoods, ...], *, freighter: bool, where: str = "the declaration"
) -> tuple[Finding, ...]:
    """Every declared line against the quantity it is allowed."""
    found = []
    for entry in entries:
        allowance = allowance_for(entry)
        if allowance is None:
            found.append(
                Finding(
                    check=UNLISTED,
                    where=where,
                    detail=(
                        f"{entry.label} is class {entry.hazard_class} and this build "
                        "has no quantity limit for it"
                    ),
                    severity=WATCH,
                )
            )
            continue
        excess = over_by(entry, freighter=freighter)
        if excess > 0:
            limit = allowance.limit(freighter=freighter)
            found.append(
                Finding(
                    check=QUANTITY,
                    where=where,
                    detail=(
                        f"{entry.label} holds {entry.net_quantity} {entry.unit} a package "
                        f"against a limit of {limit} {allowance.unit}"
                    ),
                    over_by=int(excess),
                    severity=STOP,
                )
            )
    return tuple(found)


def table() -> tuple[str, ...]:
    """The whole allowance table, for printing."""
    return tuple(allowance.describe() for allowance in ALLOWANCES)
