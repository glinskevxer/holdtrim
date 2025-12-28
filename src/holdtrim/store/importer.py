"""Reading a booking file in.

The reservations system sends a CSV overnight and it is not always right. A row
with a bad check digit or a handling code nobody has heard of has to be
reported with its line number and the rest of the file has to go in, because
holding up four hundred bookings for one typo is not a service anybody wants.

So nothing here raises on a bad row. Every row is either accepted, or reported
with the line it was on and why, and the caller decides what to do about the
report.
"""

from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from holdtrim.cargo import handling
from holdtrim.errors import HoldtrimError
from holdtrim.ids import parse_awb
from holdtrim.model.consignment import Consignment
from holdtrim.store import consignments

REQUIRED = (
    "awb",
    "origin",
    "destination",
    "pieces",
    "gross_weight",
    "volume",
    "commodity",
    "ready_on",
)
FIRST_DATA_LINE = 2


@dataclass(frozen=True)
class Rejected:
    """One row that could not be read, and why."""

    line: int
    reason: str

    def describe(self) -> str:
        """One line for the import report."""
        return f"line {self.line}: {self.reason}"


@dataclass(frozen=True)
class Outcome:
    """What an import did."""

    accepted: tuple[Consignment, ...] = ()
    rejected: tuple[Rejected, ...] = ()

    @property
    def clean(self) -> bool:
        """Whether every row went in."""
        return not self.rejected

    @property
    def weight(self) -> int:
        """The gross weight of everything accepted."""
        return sum(consignment.gross_weight for consignment in self.accepted)

    def describe(self) -> str:
        """One line for the operator."""
        return f"{len(self.accepted)} accepted, {len(self.rejected)} rejected, {self.weight} kg"


def _row(row: dict[str, str]) -> Consignment:
    codes = tuple(row.get("handling", "").replace(",", " ").split())
    unknown = handling.unknown(codes)
    if unknown:
        raise ValueError(f"handling code(s) nobody knows: {', '.join(unknown)}")
    return Consignment(
        awb=parse_awb(row["awb"]),
        origin=row["origin"],
        destination=row["destination"],
        pieces=int(row["pieces"]),
        gross_weight=int(row["gross_weight"]),
        volume=Decimal(row["volume"] or "0"),
        commodity=row["commodity"],
        ready_on=date.fromisoformat(row["ready_on"]),
        shipper=row.get("shipper", ""),
        consignee=row.get("consignee", ""),
        handling=codes,
    )


def read(text: str) -> Outcome:
    """Read a booking file without writing anything."""
    reader = csv.DictReader(io.StringIO(text))
    heads = set(reader.fieldnames or ())
    missing = [name for name in REQUIRED if name not in heads]
    if missing:
        return Outcome(rejected=(Rejected(line=1, reason=f"no {', '.join(missing)} column"),))
    accepted = []
    rejected = []
    for offset, row in enumerate(reader):
        line = offset + FIRST_DATA_LINE
        try:
            accepted.append(_row(row))
        except (HoldtrimError, ValueError, InvalidOperation, KeyError, TypeError) as exc:
            rejected.append(Rejected(line=line, reason=str(exc).strip("'")))
    return Outcome(accepted=tuple(accepted), rejected=tuple(rejected))


def load(connection: sqlite3.Connection, text: str) -> Outcome:
    """Read a booking file and put everything readable on file."""
    outcome = read(text)
    kept = []
    rejected = list(outcome.rejected)
    for offset, consignment in enumerate(outcome.accepted):
        if consignments.exists(connection, consignment.awb):
            rejected.append(
                Rejected(
                    line=offset + FIRST_DATA_LINE,
                    reason=f"waybill {consignment.awb} is already on file",
                )
            )
            continue
        consignments.add(connection, consignment)
        kept.append(consignment)
    return Outcome(accepted=tuple(kept), rejected=tuple(rejected))
