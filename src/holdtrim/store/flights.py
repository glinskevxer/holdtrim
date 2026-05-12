"""The flight file: what is scheduled, what is closed, what has gone."""

from __future__ import annotations

import sqlite3
from datetime import date

from holdtrim.errors import DuplicateError, NotFoundError, StateError
from holdtrim.ids import Flight, parse_flight, parse_registration, parse_station
from holdtrim.model.flight import PLANNED, Sector
from holdtrim.store.fleet import tail_exists
from holdtrim.store.records import counted, dropped, held
from holdtrim.store.sqlite import one, rows, transaction

COLUMNS = (
    "key, carrier, number, suffix, day, registration, origin, destination, "
    "taxi_fuel, trip_fuel, takeoff_fuel, crew, freighter, status"
)


def _sector(row: sqlite3.Row) -> Sector:
    return Sector(
        designator=Flight(
            carrier=str(row["carrier"]),
            number=int(row["number"]),
            suffix=str(row["suffix"]),
        ),
        day=date.fromisoformat(str(row["day"])),
        registration=str(row["registration"]),
        origin=str(row["origin"]),
        destination=str(row["destination"]),
        taxi_fuel=int(row["taxi_fuel"]),
        trip_fuel=int(row["trip_fuel"]),
        takeoff_fuel=int(row["takeoff_fuel"]),
        crew=int(row["crew"]),
        freighter=bool(row["freighter"]),
        status=str(row["status"]),
    )


def key_for(designator: str, day: date) -> str:
    """The filing key, built the same way wherever it is asked for."""
    return f"{parse_flight(designator)}/{day.isoformat()}"


EXISTS = "SELECT count(*) FROM sector WHERE key = ?"
DELETE = "DELETE FROM sector WHERE key = ?"
COUNT = "SELECT count(*) FROM sector"


def exists(connection: sqlite3.Connection, key: str) -> bool:
    """Whether a flight is on file."""
    return held(connection, EXISTS, key)


def add(connection: sqlite3.Connection, sector: Sector) -> Sector:
    """Put a flight on file, refusing a tail that is not on the fleet."""
    if exists(connection, sector.key):
        raise DuplicateError(f"flight {sector.key} is already on file")
    if not tail_exists(connection, sector.registration):
        raise StateError(
            f"{sector.registration} is not on the fleet, so it cannot fly {sector.key}"
        )
    with transaction(connection):
        connection.execute(
            f"INSERT INTO sector ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sector.key,
                sector.designator.carrier,
                sector.designator.number,
                sector.designator.suffix,
                sector.day.isoformat(),
                sector.registration,
                sector.origin,
                sector.destination,
                sector.taxi_fuel,
                sector.trip_fuel,
                sector.takeoff_fuel,
                sector.crew,
                int(sector.freighter),
                sector.status,
            ),
        )
    return sector


def get(connection: sqlite3.Connection, key: str) -> Sector:
    """One flight by its filing key."""
    row = one(connection, f"SELECT {COLUMNS} FROM sector WHERE key = ?", (key,))
    if row is None:
        raise NotFoundError(f"no flight {key} on file")
    return _sector(row)


def find(connection: sqlite3.Connection, designator: str, day: date) -> Sector:
    """One flight by designator and day, which is how anybody asks for one."""
    return get(connection, key_for(designator, day))


def listing(connection: sqlite3.Connection) -> list[Sector]:
    """Every flight on file, oldest first."""
    found = rows(connection, f"SELECT {COLUMNS} FROM sector ORDER BY day, carrier, number")
    return [_sector(row) for row in found]


def on_day(connection: sqlite3.Connection, day: date) -> list[Sector]:
    """The programme for one day."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM sector WHERE day = ? ORDER BY carrier, number",
        (day.isoformat(),),
    )
    return [_sector(row) for row in found]


def for_tail(connection: sqlite3.Connection, registration: str) -> list[Sector]:
    """Everything one aeroplane is down to fly."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM sector WHERE registration = ? ORDER BY day, carrier, number",
        (parse_registration(registration),),
    )
    return [_sector(row) for row in found]


def out_of(connection: sqlite3.Connection, station: str, day: date) -> list[Sector]:
    """The departures from one station on one day."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM sector WHERE origin = ? AND day = ? ORDER BY carrier, number",
        (parse_station(station), day.isoformat()),
    )
    return [_sector(row) for row in found]


def still_open(connection: sqlite3.Connection, day: date) -> list[Sector]:
    """The flights on a day whose load can still be changed."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM sector WHERE day = ? AND status = ? ORDER BY carrier, number",
        (day.isoformat(), PLANNED),
    )
    return [_sector(row) for row in found]


def save(connection: sqlite3.Connection, sector: Sector) -> Sector:
    """Overwrite a flight that is already on file."""
    if not exists(connection, sector.key):
        raise NotFoundError(f"no flight {sector.key} on file")
    with transaction(connection):
        connection.execute(
            "UPDATE sector SET registration = ?, origin = ?, destination = ?, taxi_fuel = ?, "
            "trip_fuel = ?, takeoff_fuel = ?, crew = ?, freighter = ?, status = ? WHERE key = ?",
            (
                sector.registration,
                sector.origin,
                sector.destination,
                sector.taxi_fuel,
                sector.trip_fuel,
                sector.takeoff_fuel,
                sector.crew,
                int(sector.freighter),
                sector.status,
                sector.key,
            ),
        )
    return sector


def remove(connection: sqlite3.Connection, key: str) -> None:
    """Take a flight off file."""
    dropped(
        connection,
        exists_statement=EXISTS,
        delete_statement=DELETE,
        key=key,
        missing=f"no flight {key} on file",
    )


def count(connection: sqlite3.Connection) -> int:
    """How many flights are on file."""
    return counted(connection, COUNT)
