"""One dangerous goods entry off a shipper's declaration.

A declaration lists one line per substance, and the line is what the office
copies onto the captain's notice. The fields are not free text: the UN number,
the class or division, the packing group and the packing instruction all come
off the list and they have to agree with each other.

Two of those agreements are worth stating because they catch typing errors
every week. Gases and radioactive material have no packing group at all, and
an explosive is written as a division with a compatibility group letter, not
as a bare class 1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from holdtrim.errors import DataError
from holdtrim.units import to_metres

CLASS_PATTERN = re.compile(r"^(1\.[1-6][A-S]|2\.[1-3]|3|4\.[1-3]|5\.[1-2]|6\.[1-2]|7|8|9)$")
PACKING_GROUPS = ("I", "II", "III")
NO_PACKING_GROUP_CLASSES = ("1", "2", "7")
QUANTITY_UNITS = ("kg", "L", "G", "TBq")

LOWEST_UN_NUMBER = 1
HIGHEST_UN_NUMBER = 3600


@dataclass(frozen=True)
class DangerousGoods:
    """One line of a shipper's declaration."""

    un_number: int
    proper_shipping_name: str
    hazard_class: str
    packages: int
    net_quantity: Decimal
    unit: str
    packing_group: str = ""
    packing_instruction: str = ""
    subsidiary_risks: tuple[str, ...] = ()
    cargo_aircraft_only: bool = False
    transport_index: Decimal | None = None

    def __post_init__(self) -> None:
        self._check_identity()
        self._check_risks()
        self._check_packing_group()
        object.__setattr__(self, "packing_instruction", self.packing_instruction.strip().upper())
        self._check_quantity()
        self._check_radioactivity()

    def _check_identity(self) -> None:
        """The number and the name it is shipped under."""
        if not LOWEST_UN_NUMBER <= self.un_number <= HIGHEST_UN_NUMBER:
            raise DataError(f"UN {self.un_number} is not a UN number")
        name = self.proper_shipping_name.strip()
        if not name:
            raise DataError(f"UN {self.un_number} has no proper shipping name")
        object.__setattr__(self, "proper_shipping_name", name)

    def _check_risks(self) -> None:
        """The class it is in, and anything else it is also."""
        hazard = self.hazard_class.strip().upper()
        if not CLASS_PATTERN.match(hazard):
            raise DataError(f"{hazard} is not a hazard class or division")
        object.__setattr__(self, "hazard_class", hazard)
        risks = tuple(risk.strip().upper() for risk in self.subsidiary_risks)
        for risk in risks:
            if not CLASS_PATTERN.match(risk):
                raise DataError(f"{risk} is not a subsidiary risk")
        object.__setattr__(self, "subsidiary_risks", risks)

    def _check_packing_group(self) -> None:
        """A packing group is one of three, and some classes have none at all."""
        group = self.packing_group.strip().upper()
        if group and group not in PACKING_GROUPS:
            raise DataError(f"{group} is not a packing group")
        if group and self.primary_class in NO_PACKING_GROUP_CLASSES:
            raise DataError(f"class {self.primary_class} has no packing group, {group} was given")
        object.__setattr__(self, "packing_group", group)

    def _check_quantity(self) -> None:
        """Packages, what is in one of them, and the unit that is measured in."""
        if self.packages <= 0:
            raise DataError(f"UN {self.un_number} has no packages")
        object.__setattr__(self, "net_quantity", to_metres(self.net_quantity, what="net quantity"))
        if self.net_quantity <= 0:
            raise DataError(f"UN {self.un_number} has no quantity in a package")
        if self.unit not in QUANTITY_UNITS:
            raise DataError(f"{self.unit!r} is not a quantity unit on a declaration")

    def _check_radioactivity(self) -> None:
        """Class 7 is measured in transport index, and it is not optional."""
        if self.radioactive and self.transport_index is None:
            raise DataError(f"UN {self.un_number} is radioactive and has no transport index")
        if self.transport_index is not None and self.transport_index < 0:
            raise DataError(f"UN {self.un_number} has a negative transport index")

    @property
    def primary_class(self) -> str:
        """The class without the division, so 1.4G reads as 1."""
        return self.hazard_class.split(".")[0]

    @property
    def division(self) -> str:
        """The division, blank for a class that has none."""
        parts = self.hazard_class.split(".")
        return parts[1] if len(parts) > 1 else ""

    @property
    def compatibility_group(self) -> str:
        """The letter on an explosive division, blank on anything else."""
        if self.primary_class != "1":
            return ""
        return self.hazard_class[-1]

    @property
    def explosive(self) -> bool:
        """Class 1, which is segregated by compatibility group and not by class."""
        return self.primary_class == "1"

    @property
    def radioactive(self) -> bool:
        """Class 7, which is measured in transport index and not in kilograms."""
        return self.hazard_class == "7"

    @property
    def total_quantity(self) -> Decimal:
        """Every package added up."""
        return self.net_quantity * self.packages

    @property
    def label(self) -> str:
        """The way the number is written on the package and the notice."""
        return f"UN {self.un_number}"

    @property
    def all_risks(self) -> tuple[str, ...]:
        """The primary class first, then any subsidiary risks."""
        return (self.hazard_class, *self.subsidiary_risks)

    def describe(self) -> str:
        """One line, the way it reads on the captain's notice."""
        group = f" PG {self.packing_group}" if self.packing_group else ""
        quantity = f"{self.packages} x {self.net_quantity} {self.unit}"
        return f"{self.label} {self.proper_shipping_name} {self.hazard_class}{group} {quantity}"
