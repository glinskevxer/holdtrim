"""The ULD register: what devices exist, where they are, and what state they are in."""

from __future__ import annotations

import sqlite3

from holdtrim.errors import DuplicateError, NotFoundError
from holdtrim.ids import UldCode, parse_station, parse_uld
from holdtrim.model.uld import SERVICEABLE, Uld
from holdtrim.store.records import counted, dropped, held
from holdtrim.store.sqlite import one, rows, transaction

COLUMNS = "code, type_code, serial, owner, tare, max_gross, at_station, condition, contour"


def _uld(row: sqlite3.Row) -> Uld:
    return Uld(
        code=UldCode(
            type_code=str(row["type_code"]),
            serial=str(row["serial"]),
            owner=str(row["owner"]),
        ),
        tare=int(row["tare"]),
        max_gross=int(row["max_gross"]),
        at_station=str(row["at_station"]),
        condition=str(row["condition"]),
        contour=str(row["contour"]),
    )


def _key(code: str | UldCode) -> str:
    if isinstance(code, UldCode):
        return code.formatted()
    return parse_uld(code).formatted()


EXISTS = "SELECT count(*) FROM uld WHERE code = ?"
DELETE = "DELETE FROM uld WHERE code = ?"
COUNT = "SELECT count(*) FROM uld"


def exists(connection: sqlite3.Connection, code: str | UldCode) -> bool:
    """Whether a device is on the register."""
    return held(connection, EXISTS, _key(code))


def add(connection: sqlite3.Connection, device: Uld) -> Uld:
    """Put a device on the register."""
    if exists(connection, device.code):
        raise DuplicateError(f"{device.code} is already on the ULD register")
    with transaction(connection):
        connection.execute(
            f"INSERT INTO uld ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                device.code.formatted(),
                device.code.type_code,
                device.code.serial,
                device.code.owner,
                device.tare,
                device.max_gross,
                device.at_station,
                device.condition,
                device.contour,
            ),
        )
    return device


def get(connection: sqlite3.Connection, code: str | UldCode) -> Uld:
    """One device by code."""
    key = _key(code)
    row = one(connection, f"SELECT {COLUMNS} FROM uld WHERE code = ?", (key,))
    if row is None:
        raise NotFoundError(f"no ULD {key} on the register")
    return _uld(row)


def listing(connection: sqlite3.Connection) -> list[Uld]:
    """Every device, in code order."""
    return [_uld(row) for row in rows(connection, f"SELECT {COLUMNS} FROM uld ORDER BY code")]


def at_station(
    connection: sqlite3.Connection, station: str, *, base: str = "", serviceable_only: bool = False
) -> list[Uld]:
    """The devices standing at one station, narrowed if asked."""
    where = ["at_station = ?"]
    parameters: list[object] = [parse_station(station)]
    if base:
        where.append("type_code = ?")
        parameters.append(base.strip().upper())
    if serviceable_only:
        where.append("condition = ?")
        parameters.append(SERVICEABLE)
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM uld WHERE {' AND '.join(where)} ORDER BY code",
        tuple(parameters),
    )
    return [_uld(row) for row in found]


def in_transit(connection: sqlite3.Connection) -> list[Uld]:
    """The devices that are on their way somewhere."""
    found = rows(connection, f"SELECT {COLUMNS} FROM uld WHERE at_station = '' ORDER BY code")
    return [_uld(row) for row in found]


def stock(connection: sqlite3.Connection, station: str) -> dict[str, int]:
    """How many devices of each base size stand at a station."""
    found = rows(
        connection,
        "SELECT type_code, count(*) AS held FROM uld WHERE at_station = ? "
        "GROUP BY type_code ORDER BY type_code",
        (parse_station(station),),
    )
    return {str(row["type_code"]): int(row["held"]) for row in found}


def save(connection: sqlite3.Connection, device: Uld) -> Uld:
    """Overwrite a device that is already on the register."""
    if not exists(connection, device.code):
        raise NotFoundError(f"no ULD {device.code} on the register")
    with transaction(connection):
        connection.execute(
            "UPDATE uld SET tare = ?, max_gross = ?, at_station = ?, condition = ?, "
            "contour = ? WHERE code = ?",
            (
                device.tare,
                device.max_gross,
                device.at_station,
                device.condition,
                device.contour,
                device.code.formatted(),
            ),
        )
    return device


def move(connection: sqlite3.Connection, code: str | UldCode, station: str) -> Uld:
    """Record a device as standing somewhere else."""
    device = get(connection, code)
    return save(connection, device.at(station))


def remove(connection: sqlite3.Connection, code: str | UldCode) -> None:
    """Take a device off the register."""
    key = _key(code)
    dropped(
        connection,
        exists_statement=EXISTS,
        delete_statement=DELETE,
        key=key,
        missing=f"no ULD {key} on the register",
    )


def count(connection: sqlite3.Connection) -> int:
    """How many devices are on the register."""
    return counted(connection, COUNT)
