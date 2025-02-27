"""The fleet register: what types the operation flies and how they are laid out.

Decimals are written as text on purpose. A balance arm is a decimal figure off
a published schedule and storing it as a float would introduce error the
schedule does not have, in the one place where the whole point is that the
arithmetic matches the paper.
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from holdtrim.errors import DuplicateError, NotFoundError
from holdtrim.model.aircraft import AircraftType, MacGeometry, StructuralLimits
from holdtrim.model.envelope import Envelope, EnvelopePoint
from holdtrim.model.hold import CumulativeLimit, HoldLayout
from holdtrim.model.position import Position
from holdtrim.store.sqlite import one, rows, scalar_int, transaction

ACCEPTS_SEPARATOR = "/"


def _limits(row: sqlite3.Row) -> StructuralLimits:
    return StructuralLimits(
        max_ramp=int(row["max_ramp"]),
        max_takeoff=int(row["max_takeoff"]),
        max_landing=int(row["max_landing"]),
        max_zero_fuel=int(row["max_zero_fuel"]),
    )


def _geometry(row: sqlite3.Row) -> MacGeometry:
    return MacGeometry(
        reference_arm=Decimal(str(row["reference_arm"])),
        lemac=Decimal(str(row["lemac"])),
        mac_length=Decimal(str(row["mac_length"])),
        index_constant=Decimal(str(row["index_constant"])),
        index_reference=Decimal(str(row["index_reference"])),
    )


def _position(row: sqlite3.Row) -> Position:
    accepts = str(row["accepts"])
    return Position(
        code=str(row["code"]),
        compartment=str(row["compartment"]),
        arm=Decimal(str(row["arm"])),
        max_weight=int(row["max_weight"]),
        length=Decimal(str(row["length"])),
        width=Decimal(str(row["width"])),
        max_running_load=int(row["max_running_load"]),
        max_area_load=int(row["max_area_load"]),
        accepts=tuple(accepts.split(ACCEPTS_SEPARATOR)) if accepts else (),
    )


def _layout(connection: sqlite3.Connection, code: str) -> HoldLayout:
    position_rows = rows(
        connection,
        "SELECT * FROM hold_position WHERE type_code = ? ORDER BY ordinal",
        (code,),
    )
    limit_rows = rows(
        connection,
        "SELECT * FROM cumulative_limit WHERE type_code = ? ORDER BY label",
        (code,),
    )
    return HoldLayout(
        positions=tuple(_position(row) for row in position_rows),
        cumulative=tuple(
            CumulativeLimit(
                label=str(row["label"]),
                positions=tuple(str(row["positions"]).split(ACCEPTS_SEPARATOR)),
                max_weight=int(row["max_weight"]),
            )
            for row in limit_rows
        ),
    )


def _envelopes(connection: sqlite3.Connection, code: str) -> tuple[Envelope, ...]:
    found = rows(
        connection,
        "SELECT * FROM envelope_point WHERE type_code = ? ORDER BY envelope, weight",
        (code,),
    )
    grouped: dict[str, list[EnvelopePoint]] = {}
    for row in found:
        grouped.setdefault(str(row["envelope"]), []).append(
            EnvelopePoint(
                weight=int(row["weight"]),
                forward_index=Decimal(str(row["forward_index"])),
                aft_index=Decimal(str(row["aft_index"])),
            )
        )
    return tuple(
        Envelope(name=name, points=tuple(points)) for name, points in sorted(grouped.items())
    )


def type_exists(connection: sqlite3.Connection, code: str) -> bool:
    """Whether a type code is registered."""
    wanted = code.strip().upper()
    return (
        scalar_int(connection, "SELECT count(*) FROM aircraft_type WHERE code = ?", (wanted,)) > 0
    )


def add_type(connection: sqlite3.Connection, kind: AircraftType) -> AircraftType:
    """Register a type with its layout and its envelopes, all in one go."""
    if type_exists(connection, kind.code):
        raise DuplicateError(f"type {kind.code} is already in the fleet register")
    with transaction(connection):
        connection.execute(
            "INSERT INTO aircraft_type (code, name, max_ramp, max_takeoff, max_landing, "
            "max_zero_fuel, reference_arm, lemac, mac_length, index_constant, "
            "index_reference, empty_weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                kind.code,
                kind.name,
                kind.limits.max_ramp,
                kind.limits.max_takeoff,
                kind.limits.max_landing,
                kind.limits.max_zero_fuel,
                str(kind.geometry.reference_arm),
                str(kind.geometry.lemac),
                str(kind.geometry.mac_length),
                str(kind.geometry.index_constant),
                str(kind.geometry.index_reference),
                kind.empty_weight,
            ),
        )
        for ordinal, position in enumerate(kind.layout.positions):
            connection.execute(
                "INSERT INTO hold_position (type_code, code, ordinal, compartment, arm, "
                "max_weight, length, width, max_running_load, max_area_load, accepts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    kind.code,
                    position.code,
                    ordinal,
                    position.compartment,
                    str(position.arm),
                    position.max_weight,
                    str(position.length),
                    str(position.width),
                    position.max_running_load,
                    position.max_area_load,
                    ACCEPTS_SEPARATOR.join(position.accepts),
                ),
            )
        for limit in kind.layout.cumulative:
            connection.execute(
                "INSERT INTO cumulative_limit (type_code, label, max_weight, positions) "
                "VALUES (?, ?, ?, ?)",
                (
                    kind.code,
                    limit.label,
                    limit.max_weight,
                    ACCEPTS_SEPARATOR.join(limit.positions),
                ),
            )
        for envelope in kind.envelopes:
            for point in envelope.points:
                connection.execute(
                    "INSERT INTO envelope_point (type_code, envelope, weight, forward_index, "
                    "aft_index) VALUES (?, ?, ?, ?, ?)",
                    (
                        kind.code,
                        envelope.name,
                        point.weight,
                        str(point.forward_index),
                        str(point.aft_index),
                    ),
                )
    return kind


def get_type(connection: sqlite3.Connection, code: str) -> AircraftType:
    """One type, rebuilt from its rows."""
    wanted = code.strip().upper()
    row = one(connection, "SELECT * FROM aircraft_type WHERE code = ?", (wanted,))
    if row is None:
        raise NotFoundError(f"no type {wanted} in the fleet register")
    return AircraftType(
        code=str(row["code"]),
        name=str(row["name"]),
        limits=_limits(row),
        geometry=_geometry(row),
        layout=_layout(connection, wanted),
        envelopes=_envelopes(connection, wanted),
        empty_weight=int(row["empty_weight"]),
    )


def list_types(connection: sqlite3.Connection) -> list[AircraftType]:
    """Every registered type, in code order."""
    codes = [
        str(row["code"]) for row in rows(connection, "SELECT code FROM aircraft_type ORDER BY code")
    ]
    return [get_type(connection, code) for code in codes]


def remove_type(connection: sqlite3.Connection, code: str) -> None:
    """Take a type out, layout and envelopes with it."""
    wanted = code.strip().upper()
    if not type_exists(connection, wanted):
        raise NotFoundError(f"no type {wanted} in the fleet register")
    with transaction(connection):
        connection.execute("DELETE FROM aircraft_type WHERE code = ?", (wanted,))


def count_types(connection: sqlite3.Connection) -> int:
    """How many types are registered."""
    return scalar_int(connection, "SELECT count(*) FROM aircraft_type")
