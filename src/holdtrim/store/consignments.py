"""The waybill file: what is booked, what is in the shed, what is ready to fly."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from holdtrim.errors import DuplicateError, NotFoundError
from holdtrim.ids import AirWaybill, parse_awb, parse_station
from holdtrim.model.consignment import Consignment
from holdtrim.store.records import counted, dropped, held
from holdtrim.store.sqlite import one, rows, scalar_int, transaction

HANDLING_SEPARATOR = " "
COLUMNS = (
    "awb, prefix, serial, origin, destination, pieces, gross_weight, volume, "
    "commodity, ready_on, shipper, consignee, handling"
)


def _consignment(row: sqlite3.Row) -> Consignment:
    handling = str(row["handling"])
    return Consignment(
        awb=AirWaybill(prefix=str(row["prefix"]), serial=int(row["serial"])),
        origin=str(row["origin"]),
        destination=str(row["destination"]),
        pieces=int(row["pieces"]),
        gross_weight=int(row["gross_weight"]),
        volume=Decimal(str(row["volume"])),
        commodity=str(row["commodity"]),
        ready_on=date.fromisoformat(str(row["ready_on"])),
        shipper=str(row["shipper"]),
        consignee=str(row["consignee"]),
        handling=tuple(handling.split(HANDLING_SEPARATOR)) if handling else (),
    )


def _key(awb: str | AirWaybill) -> str:
    if isinstance(awb, AirWaybill):
        return awb.plain()
    return parse_awb(awb).plain()


EXISTS = "SELECT count(*) FROM consignment WHERE awb = ?"
DELETE = "DELETE FROM consignment WHERE awb = ?"
COUNT = "SELECT count(*) FROM consignment"


def exists(connection: sqlite3.Connection, awb: str | AirWaybill) -> bool:
    """Whether a waybill is on file."""
    return held(connection, EXISTS, _key(awb))


def add(connection: sqlite3.Connection, consignment: Consignment) -> Consignment:
    """Put a waybill on file."""
    if exists(connection, consignment.awb):
        raise DuplicateError(f"waybill {consignment.awb} is already on file")
    with transaction(connection):
        connection.execute(
            f"INSERT INTO consignment ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                consignment.awb.plain(),
                consignment.awb.prefix,
                consignment.awb.serial,
                consignment.origin,
                consignment.destination,
                consignment.pieces,
                consignment.gross_weight,
                str(consignment.volume),
                consignment.commodity,
                consignment.ready_on.isoformat(),
                consignment.shipper,
                consignment.consignee,
                HANDLING_SEPARATOR.join(consignment.handling),
            ),
        )
    return consignment


def get(connection: sqlite3.Connection, awb: str | AirWaybill) -> Consignment:
    """One waybill by number."""
    key = _key(awb)
    row = one(connection, f"SELECT {COLUMNS} FROM consignment WHERE awb = ?", (key,))
    if row is None:
        raise NotFoundError(f"no waybill {key} on file")
    return _consignment(row)


def listing(connection: sqlite3.Connection) -> list[Consignment]:
    """Every waybill on file, in number order."""
    found = rows(connection, f"SELECT {COLUMNS} FROM consignment ORDER BY awb")
    return [_consignment(row) for row in found]


def on_route(connection: sqlite3.Connection, origin: str, destination: str) -> list[Consignment]:
    """Every waybill booked over one sector, oldest ready date first."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM consignment WHERE origin = ? AND destination = ? "
        "ORDER BY ready_on, awb",
        (parse_station(origin), parse_station(destination)),
    )
    return [_consignment(row) for row in found]


def ready_by(
    connection: sqlite3.Connection, origin: str, destination: str, on: date
) -> list[Consignment]:
    """What is available to load on a sector by a given day."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM consignment WHERE origin = ? AND destination = ? "
        "AND ready_on <= ? ORDER BY ready_on, awb",
        (parse_station(origin), parse_station(destination), on.isoformat()),
    )
    return [_consignment(row) for row in found]


def save(connection: sqlite3.Connection, consignment: Consignment) -> Consignment:
    """Overwrite a waybill that is already on file."""
    if not exists(connection, consignment.awb):
        raise NotFoundError(f"no waybill {consignment.awb} on file")
    with transaction(connection):
        connection.execute(
            "UPDATE consignment SET origin = ?, destination = ?, pieces = ?, "
            "gross_weight = ?, volume = ?, commodity = ?, ready_on = ?, shipper = ?, "
            "consignee = ?, handling = ? WHERE awb = ?",
            (
                consignment.origin,
                consignment.destination,
                consignment.pieces,
                consignment.gross_weight,
                str(consignment.volume),
                consignment.commodity,
                consignment.ready_on.isoformat(),
                consignment.shipper,
                consignment.consignee,
                HANDLING_SEPARATOR.join(consignment.handling),
                consignment.awb.plain(),
            ),
        )
    return consignment


def remove(connection: sqlite3.Connection, awb: str | AirWaybill) -> None:
    """Take a waybill off file."""
    key = _key(awb)
    dropped(
        connection,
        exists_statement=EXISTS,
        delete_statement=DELETE,
        key=key,
        missing=f"no waybill {key} on file",
    )


def count(connection: sqlite3.Connection) -> int:
    """How many waybills are on file."""
    return counted(connection, COUNT)


def tonnage(connection: sqlite3.Connection, origin: str, destination: str) -> int:
    """The gross weight booked over a sector."""
    return scalar_int(
        connection,
        "SELECT coalesce(sum(gross_weight), 0) FROM consignment "
        "WHERE origin = ? AND destination = ?",
        (parse_station(origin), parse_station(destination)),
    )
