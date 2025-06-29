"""Storing load plans.

A plan is written whole every time. The alternative, updating single
assignments in place, sounds cheaper and is how the first version of this
worked, and it left plans that were half of one edition and half of another
after a crash between two writes. A plan is small and a flight is planned a
handful of times, so it is written as one row and its assignments in one
transaction.
"""

from __future__ import annotations

import sqlite3

from holdtrim.errors import NotFoundError, StateError
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.store.flights import exists as flight_exists
from holdtrim.store.sqlite import one, rows, scalar_int, transaction

COLUMNS = "flight_key, hold_position, ordinal, weight, uld, destination"


def _assignment(row: sqlite3.Row) -> Assignment:
    return Assignment(
        position=str(row["hold_position"]),
        weight=int(row["weight"]),
        uld=str(row["uld"]),
        destination=str(row["destination"]),
    )


def exists(connection: sqlite3.Connection, flight_key: str) -> bool:
    """Whether a flight has a plan."""
    sql = "SELECT count(*) FROM load_plan WHERE flight_key = ?"
    return scalar_int(connection, sql, (flight_key,)) > 0


def save(connection: sqlite3.Connection, plan: LoadPlan) -> LoadPlan:
    """Write a plan, replacing whatever was there."""
    if not flight_exists(connection, plan.flight_key):
        raise StateError(f"no flight {plan.flight_key} on file to plan a load for")
    with transaction(connection):
        connection.execute(
            "INSERT INTO load_plan (flight_key, edition) VALUES (?, ?) "
            "ON CONFLICT (flight_key) DO UPDATE SET edition = excluded.edition",
            (plan.flight_key, plan.edition),
        )
        connection.execute("DELETE FROM plan_assignment WHERE flight_key = ?", (plan.flight_key,))
        for ordinal, assignment in enumerate(plan.assignments):
            connection.execute(
                f"INSERT INTO plan_assignment ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    plan.flight_key,
                    assignment.position,
                    ordinal,
                    assignment.weight,
                    assignment.uld,
                    assignment.destination,
                ),
            )
    return plan


def get(connection: sqlite3.Connection, flight_key: str) -> LoadPlan:
    """One flight's plan."""
    row = one(connection, "SELECT edition FROM load_plan WHERE flight_key = ?", (flight_key,))
    if row is None:
        raise NotFoundError(f"no load plan for flight {flight_key}")
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM plan_assignment WHERE flight_key = ? ORDER BY ordinal",
        (flight_key,),
    )
    return LoadPlan(
        flight_key=flight_key,
        assignments=tuple(_assignment(entry) for entry in found),
        edition=int(row["edition"]),
    )


def get_or_start(connection: sqlite3.Connection, flight_key: str) -> LoadPlan:
    """The flight's plan, or an empty one at edition one."""
    if exists(connection, flight_key):
        return get(connection, flight_key)
    if not flight_exists(connection, flight_key):
        raise StateError(f"no flight {flight_key} on file to plan a load for")
    return LoadPlan(flight_key=flight_key)


def remove(connection: sqlite3.Connection, flight_key: str) -> None:
    """Throw a plan away."""
    if not exists(connection, flight_key):
        raise NotFoundError(f"no load plan for flight {flight_key}")
    with transaction(connection):
        connection.execute("DELETE FROM load_plan WHERE flight_key = ?", (flight_key,))


def flights_carrying(connection: sqlite3.Connection, uld: str) -> list[str]:
    """Which flights have a device planned on them."""
    found = rows(
        connection,
        "SELECT DISTINCT flight_key FROM plan_assignment WHERE uld = ? ORDER BY flight_key",
        (uld.strip().upper(),),
    )
    return [str(row["flight_key"]) for row in found]


def count(connection: sqlite3.Connection) -> int:
    """How many plans are stored."""
    return scalar_int(connection, "SELECT count(*) FROM load_plan")
