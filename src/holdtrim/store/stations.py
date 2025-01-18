"""Reading and writing the station register."""

from __future__ import annotations

import sqlite3

from holdtrim.errors import DuplicateError, NotFoundError
from holdtrim.ids import parse_station
from holdtrim.model.station import Station
from holdtrim.store.sqlite import one, rows, scalar_int, transaction

COLUMNS = "code, name, elevation_feet, handling_agent, free_storage_days"


def _station(row: sqlite3.Row) -> Station:
    return Station(
        code=str(row["code"]),
        name=str(row["name"]),
        elevation_feet=int(row["elevation_feet"]),
        handling_agent=str(row["handling_agent"]),
        free_storage_days=int(row["free_storage_days"]),
    )


def add(connection: sqlite3.Connection, station: Station) -> Station:
    """Put a station in the register, refusing a code that is already there."""
    if exists(connection, station.code):
        raise DuplicateError(f"station {station.code} is already in the register")
    with transaction(connection):
        connection.execute(
            f"INSERT INTO station ({COLUMNS}) VALUES (?, ?, ?, ?, ?)",
            (
                station.code,
                station.name,
                station.elevation_feet,
                station.handling_agent,
                station.free_storage_days,
            ),
        )
    return station


def exists(connection: sqlite3.Connection, code: str) -> bool:
    """Whether a code is in the register, without raising if it is not."""
    wanted = parse_station(code)
    return scalar_int(connection, "SELECT count(*) FROM station WHERE code = ?", (wanted,)) > 0


def get(connection: sqlite3.Connection, code: str) -> Station:
    """One station by code, or say plainly that it is not there."""
    wanted = parse_station(code)
    row = one(connection, f"SELECT {COLUMNS} FROM station WHERE code = ?", (wanted,))
    if row is None:
        raise NotFoundError(f"no station {wanted} in the register")
    return _station(row)


def listing(connection: sqlite3.Connection) -> list[Station]:
    """Every station, in code order."""
    return [
        _station(row) for row in rows(connection, f"SELECT {COLUMNS} FROM station ORDER BY code")
    ]


def save(connection: sqlite3.Connection, station: Station) -> Station:
    """Overwrite a station that is already registered."""
    if not exists(connection, station.code):
        raise NotFoundError(f"no station {station.code} in the register")
    with transaction(connection):
        connection.execute(
            "UPDATE station SET name = ?, elevation_feet = ?, handling_agent = ?, "
            "free_storage_days = ? WHERE code = ?",
            (
                station.name,
                station.elevation_feet,
                station.handling_agent,
                station.free_storage_days,
                station.code,
            ),
        )
    return station


def remove(connection: sqlite3.Connection, code: str) -> None:
    """Take a station out of the register."""
    wanted = parse_station(code)
    if not exists(connection, wanted):
        raise NotFoundError(f"no station {wanted} in the register")
    with transaction(connection):
        connection.execute("DELETE FROM station WHERE code = ?", (wanted,))


def count(connection: sqlite3.Connection) -> int:
    """How many stations the register holds."""
    return scalar_int(connection, "SELECT count(*) FROM station")
