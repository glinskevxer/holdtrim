"""The dangerous goods declared against a waybill.

One waybill can carry several lines, and the lines are what the captain's
notice is built from, so they are stored as they were declared rather than
summarised. A summary is something a report makes; the declaration is what was
signed.
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from holdtrim.errors import NotFoundError, StateError
from holdtrim.ids import AirWaybill, parse_awb
from holdtrim.model.danger import DangerousGoods
from holdtrim.store import consignments
from holdtrim.store.sqlite import rows, scalar_int, transaction

RISK_SEPARATOR = " "
COLUMNS = (
    "awb, un_number, proper_shipping_name, hazard_class, packages, net_quantity, "
    "unit, packing_group, packing_instruction, subsidiary_risks, cargo_aircraft_only, "
    "transport_index"
)


def _entry(row: sqlite3.Row) -> DangerousGoods:
    risks = str(row["subsidiary_risks"])
    index = str(row["transport_index"])
    return DangerousGoods(
        un_number=int(row["un_number"]),
        proper_shipping_name=str(row["proper_shipping_name"]),
        hazard_class=str(row["hazard_class"]),
        packages=int(row["packages"]),
        net_quantity=Decimal(str(row["net_quantity"])),
        unit=str(row["unit"]),
        packing_group=str(row["packing_group"]),
        packing_instruction=str(row["packing_instruction"]),
        subsidiary_risks=tuple(risks.split(RISK_SEPARATOR)) if risks else (),
        cargo_aircraft_only=bool(row["cargo_aircraft_only"]),
        transport_index=Decimal(index) if index else None,
    )


def _key(awb: str | AirWaybill) -> str:
    if isinstance(awb, AirWaybill):
        return awb.plain()
    return parse_awb(awb).plain()


def declare(
    connection: sqlite3.Connection, awb: str | AirWaybill, entry: DangerousGoods
) -> DangerousGoods:
    """Add one declared line against a waybill that is on file."""
    key = _key(awb)
    if not consignments.exists(connection, key):
        raise StateError(f"waybill {key} is not on file, so nothing can be declared against it")
    with transaction(connection):
        connection.execute(
            f"INSERT INTO dangerous_goods ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                key,
                entry.un_number,
                entry.proper_shipping_name,
                entry.hazard_class,
                entry.packages,
                str(entry.net_quantity),
                entry.unit,
                entry.packing_group,
                entry.packing_instruction,
                RISK_SEPARATOR.join(entry.subsidiary_risks),
                int(entry.cargo_aircraft_only),
                "" if entry.transport_index is None else str(entry.transport_index),
            ),
        )
    return entry


def against(connection: sqlite3.Connection, awb: str | AirWaybill) -> tuple[DangerousGoods, ...]:
    """Every line declared against one waybill."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM dangerous_goods WHERE awb = ? ORDER BY id",
        (_key(awb),),
    )
    return tuple(_entry(row) for row in found)


def waybills(connection: sqlite3.Connection) -> list[str]:
    """Every waybill with anything declared against it."""
    found = rows(connection, "SELECT DISTINCT awb FROM dangerous_goods ORDER BY awb")
    return [str(row["awb"]) for row in found]


def clear(connection: sqlite3.Connection, awb: str | AirWaybill) -> int:
    """Take every declared line off a waybill, and say how many went."""
    key = _key(awb)
    held = len(against(connection, key))
    if not held:
        raise NotFoundError(f"nothing is declared against waybill {key}")
    with transaction(connection):
        connection.execute("DELETE FROM dangerous_goods WHERE awb = ?", (key,))
    return held


def count(connection: sqlite3.Connection) -> int:
    """How many declared lines the book holds."""
    return scalar_int(connection, "SELECT count(*) FROM dangerous_goods")
