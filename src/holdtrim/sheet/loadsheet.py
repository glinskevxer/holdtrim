"""The loadsheet, as figures rather than as paper.

Everything on a loadsheet is derived from four things: the aeroplane, the
flight, the plan and the schedule. Nothing here is entered by hand except the
name of whoever prepared it, and that is the point. A figure typed onto a
loadsheet is a figure nobody can trace back, and tracing figures back is the
whole job when something goes wrong later.

The distribution is grouped by compartment because that is how the loading
instruction reads and how the crew think about the aeroplane, not by position
number, which is how the plan is stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from holdtrim.balance.limits import check
from holdtrim.balance.loading import Balance, load_positions
from holdtrim.errors import RuleError
from holdtrim.findings import Finding
from holdtrim.model.aircraft import AircraftType
from holdtrim.model.flight import Sector
from holdtrim.model.tail import Tail
from holdtrim.plan.lmc import Changes, applied, check_tolerance
from holdtrim.plan.loadplan import LoadPlan
from holdtrim.units import to_percent


@dataclass(frozen=True)
class Loadsheet:
    """One edition of one flight's loadsheet."""

    sector: Sector
    tail: Tail
    kind: AircraftType
    plan: LoadPlan
    balance: Balance
    prepared_by: str
    edition: int = 1
    changes: Changes = field(default_factory=Changes)

    @property
    def reference(self) -> str:
        """How the sheet names itself."""
        return f"{self.sector.reference} {self.tail.registration} edition {self.edition}"

    @property
    def dry_operating_weight(self) -> int:
        """What the aeroplane weighs before anything is put in it."""
        return self.tail.dry_operating_weight

    @property
    def payload(self) -> int:
        """Everything loaded."""
        return self.balance.payload

    @property
    def by_compartment(self) -> dict[str, int]:
        """What each compartment is carrying, in layout order."""
        carried: dict[str, int] = {}
        for position, weight in self.balance.loaded_positions.items():
            compartment = self.kind.layout.position(position).compartment
            carried[compartment] = carried.get(compartment, 0) + weight
        return carried

    @property
    def by_destination(self) -> dict[str, int]:
        """What is on board for each offload point."""
        carried: dict[str, int] = {}
        for assignment in self.plan.assignments:
            where = assignment.destination or self.sector.destination
            carried[where] = carried.get(where, 0) + assignment.weight
        return dict(sorted(carried.items()))

    @property
    def zero_fuel_percent_mac(self) -> Decimal:
        """The centre of gravity at zero fuel weight."""
        return self.balance.zero_fuel.percent_mac(self.kind)

    @property
    def takeoff_percent_mac(self) -> Decimal:
        """The centre of gravity at takeoff weight, which sets the trim."""
        return self.balance.takeoff.percent_mac(self.kind)

    @property
    def landing_percent_mac(self) -> Decimal:
        """The centre of gravity at landing weight."""
        return self.balance.landing.percent_mac(self.kind)

    @property
    def trim_setting(self) -> Decimal:
        """The stabiliser setting the crew put in before the roll."""
        return self.kind.trim.setting_at(self.takeoff_percent_mac)

    @property
    def underload(self) -> int:
        """How much more could have been carried."""
        return self.balance.underload

    @property
    def limiting_weight(self) -> str:
        """Which of the three limits was the binding one."""
        return self.balance.limiting_weight

    @property
    def findings(self) -> tuple[Finding, ...]:
        """Everything wrong with the figures, empty on a sheet that may be signed."""
        return check(self.balance)

    @property
    def signable(self) -> bool:
        """Whether this sheet may be handed over as it stands."""
        return not self.findings and self.changes.within_tolerance

    def issue(self) -> Loadsheet:
        """Confirm the sheet, refusing to issue one with a finding on it."""
        if self.findings:
            raise RuleError(
                f"{self.reference} cannot be issued, {len(self.findings)} check(s) failed"
            )
        check_tolerance(self.changes)
        return self

    def reissued(self) -> Loadsheet:
        """The next edition of the same sheet."""
        return Loadsheet(
            sector=self.sector,
            tail=self.tail,
            kind=self.kind,
            plan=self.plan.reissued(),
            balance=self.balance,
            prepared_by=self.prepared_by,
            edition=self.edition + 1,
        )

    def summary(self) -> str:
        """The one line a handover note carries."""
        return (
            f"{self.reference} ZFW {self.balance.zero_fuel.weight} "
            f"TOW {self.balance.takeoff.weight} "
            f"MAC {to_percent(self.takeoff_percent_mac)} "
            f"trim {self.trim_setting}"
        )


def after_changes(sheet: Loadsheet, changes: Changes) -> Loadsheet:
    """The same sheet with last minute changes worked all the way through.

    The plan, the balance and the findings all move together. Applying a change
    to one of them and not the others is how a sheet ends up saying two
    different things about the same aeroplane.
    """
    plan = applied(sheet.plan, changes)
    balance = Balance(
        kind=sheet.kind,
        tail=sheet.tail,
        loads=load_positions(sheet.kind, plan.weights),
        taxi_fuel=sheet.balance.taxi_fuel,
        trip_fuel=sheet.balance.trip_fuel,
        takeoff_fuel=sheet.balance.takeoff_fuel,
    )
    return Loadsheet(
        sector=sheet.sector,
        tail=sheet.tail,
        kind=sheet.kind,
        plan=plan,
        balance=balance,
        prepared_by=sheet.prepared_by,
        edition=sheet.edition,
        changes=changes,
    )
