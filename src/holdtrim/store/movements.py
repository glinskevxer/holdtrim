"""The movement log, which is added to and never edited."""

from __future__ import annotations

import sqlite3
from datetime import date

from holdtrim.errors import NotFoundError
from holdtrim.ids import UldCode, parse_station, parse_uld
from holdtrim.model.movement import ARRIVED, Movement
from holdtrim.store.sqlite import one, rows, scalar_int, transaction

COLUMNS = "day, station, uld, type_code, serial, owner, direction, flight_key, state, note"


def _movement(row: sqlite3.Row) -> Movement:
    return Movement(
        day=date.fromisoformat(str(row["day"])),
        station=str(row["station"]),
        uld=UldCode(
            type_code=str(row["type_code"]),
            serial=str(row["serial"]),
            owner=str(row["owner"]),
        ),
        direction=str(row["direction"]),
        flight_key=str(row["flight_key"]),
        state=str(row["state"]),
        note=str(row["note"]),
    )


def record(connection: sqlite3.Connection, moved: Movement) -> Movement:
    """Add a movement to the log."""
    with transaction(connection):
        connection.execute(
            f"INSERT INTO uld_movement ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                moved.day.isoformat(),
                moved.station,
                moved.uld.formatted(),
                moved.uld.type_code,
                moved.uld.serial,
                moved.uld.owner,
                moved.direction,
                moved.flight_key,
                moved.state,
                moved.note,
            ),
        )
    return moved


def listing(connection: sqlite3.Connection) -> list[Movement]:
    """Every movement, oldest first."""
    found = rows(connection, f"SELECT {COLUMNS} FROM uld_movement ORDER BY day, id")
    return [_movement(row) for row in found]


def for_uld(connection: sqlite3.Connection, code: str) -> list[Movement]:
    """One device's whole history."""
    wanted = parse_uld(code).formatted()
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM uld_movement WHERE uld = ? ORDER BY day, id",
        (wanted,),
    )
    return [_movement(row) for row in found]


def at_station(
    connection: sqlite3.Connection,
    station: str,
    *,
    since: date | None = None,
    until: date | None = None,
) -> list[Movement]:
    """Everything that crossed a station's boundary, oldest first."""
    where = ["station = ?"]
    parameters: list[object] = [parse_station(station)]
    if since is not None:
        where.append("day >= ?")
        parameters.append(since.isoformat())
    if until is not None:
        where.append("day <= ?")
        parameters.append(until.isoformat())
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM uld_movement WHERE {' AND '.join(where)} ORDER BY day, id",
        tuple(parameters),
    )
    return [_movement(row) for row in found]


def for_flight(connection: sqlite3.Connection, flight_key: str) -> list[Movement]:
    """Everything that moved on one flight.

    This used to be done by reading the whole log and filtering in Python,
    which is fine for a season and not fine for a book that has been worked for
    two. There is an index on the flight now.
    """
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM uld_movement WHERE flight_key = ? ORDER BY day, id",
        (flight_key,),
    )
    return [_movement(row) for row in found]


def balance(connection: sqlite3.Connection, station: str, on: date) -> dict[str, int]:
    """How many of each base size the log says a station holds on a day."""
    held: dict[str, int] = {}
    for moved in at_station(connection, station, until=on):
        held[moved.base] = held.get(moved.base, 0) + moved.effect
    return {base: count for base, count in sorted(held.items()) if count}


def last_seen(connection: sqlite3.Connection, code: str) -> Movement:
    """The most recent movement of one device."""
    wanted = parse_uld(code).formatted()
    row = one(
        connection,
        f"SELECT {COLUMNS} FROM uld_movement WHERE uld = ? ORDER BY day DESC, id DESC LIMIT 1",
        (wanted,),
    )
    if row is None:
        raise NotFoundError(f"no movement has ever been recorded for {wanted}")
    return _movement(row)


def standing_since(connection: sqlite3.Connection, code: str) -> date:
    """The day a device arrived where it is now."""
    moved = last_seen(connection, code)
    if moved.direction != ARRIVED:
        raise NotFoundError(f"{moved.uld} left {moved.station} on {moved.day.isoformat()}")
    return moved.day


def count(connection: sqlite3.Connection) -> int:
    """How many movements are in the log."""
    return scalar_int(connection, "SELECT count(*) FROM uld_movement")
