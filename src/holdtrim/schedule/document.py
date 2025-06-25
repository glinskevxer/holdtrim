"""Reading a weight schedule in and writing one back out.

A schedule arrives as a document, from the operator's engineering department
or from the lessor, and it is typed up once and then trusted for years. So the
reader is strict and says exactly which field it could not read, rather than
filling a default in and letting a wrong arm reach a loadsheet.

Every decimal is written as a string in the document on purpose, for the same
reason the store holds them as text.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from holdtrim.balance.fuel import FuelPoint, FuelTable
from holdtrim.balance.trim import TrimPoint, TrimTable
from holdtrim.errors import DataError
from holdtrim.model.aircraft import AircraftType, MacGeometry, StructuralLimits
from holdtrim.model.envelope import Envelope, EnvelopePoint
from holdtrim.model.hold import CumulativeLimit, HoldLayout
from holdtrim.model.position import Position

LIMIT_FIELDS = ("max_ramp", "max_takeoff", "max_landing", "max_zero_fuel")
GEOMETRY_FIELDS = (
    "reference_arm",
    "lemac",
    "mac_length",
    "index_constant",
    "index_reference",
)
POSITION_FIELDS = (
    "code",
    "compartment",
    "arm",
    "max_weight",
    "length",
    "width",
    "max_running_load",
    "max_area_load",
)


def _mapping(value: object, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DataError(f"{where} in the schedule is not a block of fields")
    return value


def _need(block: dict[str, Any], key: str, where: str) -> Any:
    if key not in block:
        raise DataError(f"the schedule is missing {key} in {where}")
    return block[key]


def _whole(block: dict[str, Any], key: str, where: str) -> int:
    value = _need(block, key, where)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataError(f"{key} in {where} is not a whole number of kilograms: {value!r}")
    whole: int = value
    return whole


def _decimal(block: dict[str, Any], key: str, where: str) -> Decimal:
    value = _need(block, key, where)
    if not isinstance(value, str):
        raise DataError(f"{key} in {where} has to be written as text, not as {value!r}")
    try:
        return Decimal(value)
    except InvalidOperation:
        raise DataError(f"{key} in {where} is not a number: {value!r}") from None


def _limits(block: dict[str, Any]) -> StructuralLimits:
    where = "limits"
    return StructuralLimits(**{field: _whole(block, field, where) for field in LIMIT_FIELDS})


def _geometry(block: dict[str, Any]) -> MacGeometry:
    where = "geometry"
    return MacGeometry(**{field: _decimal(block, field, where) for field in GEOMETRY_FIELDS})


def _position(block: dict[str, Any]) -> Position:
    where = f"position {block.get('code', '(unnamed)')}"
    accepts = block.get("accepts", [])
    if not isinstance(accepts, list):
        raise DataError(f"accepts in {where} is not a list of base sizes")
    return Position(
        code=str(_need(block, "code", where)),
        compartment=str(_need(block, "compartment", where)),
        arm=_decimal(block, "arm", where),
        max_weight=_whole(block, "max_weight", where),
        length=_decimal(block, "length", where),
        width=_decimal(block, "width", where),
        max_running_load=_whole(block, "max_running_load", where),
        max_area_load=_whole(block, "max_area_load", where),
        accepts=tuple(str(base) for base in accepts),
    )


def _cumulative(block: dict[str, Any]) -> CumulativeLimit:
    where = f"cumulative limit {block.get('label', '(unnamed)')}"
    positions = _need(block, "positions", where)
    if not isinstance(positions, list):
        raise DataError(f"positions in {where} is not a list")
    return CumulativeLimit(
        label=str(_need(block, "label", where)),
        positions=tuple(str(code) for code in positions),
        max_weight=_whole(block, "max_weight", where),
    )


def _envelope(name: str, points: object) -> Envelope:
    where = f"the {name} envelope"
    if not isinstance(points, list) or not points:
        raise DataError(f"{where} has no breakpoints")
    read = []
    for entry in points:
        block = _mapping(entry, where)
        read.append(
            EnvelopePoint(
                weight=_whole(block, "weight", where),
                forward_index=_decimal(block, "forward_index", where),
                aft_index=_decimal(block, "aft_index", where),
            )
        )
    return Envelope(name=name, points=tuple(read))


def _fuel(rows: object) -> FuelTable:
    where = "the fuel index table"
    if not isinstance(rows, list) or not rows:
        raise DataError(f"{where} has no rows")
    read = []
    for entry in rows:
        block = _mapping(entry, where)
        read.append(
            FuelPoint(
                weight=_whole(block, "weight", where),
                index=_decimal(block, "index", where),
            )
        )
    return FuelTable(points=tuple(read))


def _trim(rows: object) -> TrimTable:
    where = "the trim table"
    if not isinstance(rows, list) or not rows:
        raise DataError(f"{where} has no rows")
    read = []
    for entry in rows:
        block = _mapping(entry, where)
        read.append(
            TrimPoint(
                percent_mac=_decimal(block, "percent_mac", where),
                setting=_decimal(block, "setting", where),
            )
        )
    return TrimTable(points=tuple(read))


def read_schedule(text: str) -> AircraftType:
    """Read a weight schedule document into a type."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataError(f"the schedule is not readable: {exc.msg} at line {exc.lineno}") from None
    document = _mapping(parsed, "the schedule")
    positions = _need(document, "positions", "the schedule")
    if not isinstance(positions, list) or not positions:
        raise DataError("the schedule lists no positions")
    envelopes = _mapping(_need(document, "envelopes", "the schedule"), "envelopes")
    return AircraftType(
        code=str(_need(document, "code", "the schedule")),
        name=str(_need(document, "name", "the schedule")),
        limits=_limits(_mapping(_need(document, "limits", "the schedule"), "limits")),
        geometry=_geometry(_mapping(_need(document, "geometry", "the schedule"), "geometry")),
        layout=HoldLayout(
            positions=tuple(_position(_mapping(entry, "a position")) for entry in positions),
            cumulative=tuple(
                _cumulative(_mapping(entry, "a cumulative limit"))
                for entry in document.get("cumulative", [])
            ),
        ),
        envelopes=tuple(_envelope(name, points) for name, points in sorted(envelopes.items())),
        fuel=_fuel(_need(document, "fuel", "the schedule")),
        trim=_trim(_need(document, "trim", "the schedule")),
        empty_weight=int(document.get("empty_weight", 0)),
    )


def write_schedule(kind: AircraftType) -> str:
    """Write a type back out as the document it was read from."""
    document = {
        "code": kind.code,
        "name": kind.name,
        "empty_weight": kind.empty_weight,
        "limits": kind.limits.as_dict(),
        "geometry": {
            "reference_arm": str(kind.geometry.reference_arm),
            "lemac": str(kind.geometry.lemac),
            "mac_length": str(kind.geometry.mac_length),
            "index_constant": str(kind.geometry.index_constant),
            "index_reference": str(kind.geometry.index_reference),
        },
        "positions": [
            {
                "code": position.code,
                "compartment": position.compartment,
                "arm": str(position.arm),
                "max_weight": position.max_weight,
                "length": str(position.length),
                "width": str(position.width),
                "max_running_load": position.max_running_load,
                "max_area_load": position.max_area_load,
                "accepts": list(position.accepts),
            }
            for position in kind.layout.positions
        ],
        "cumulative": [
            {
                "label": limit.label,
                "positions": list(limit.positions),
                "max_weight": limit.max_weight,
            }
            for limit in kind.layout.cumulative
        ],
        "fuel": [{"weight": point.weight, "index": str(point.index)} for point in kind.fuel.points],
        "trim": [
            {"percent_mac": str(point.percent_mac), "setting": str(point.setting)}
            for point in kind.trim.points
        ],
        "envelopes": {
            envelope.name: [
                {
                    "weight": point.weight,
                    "forward_index": str(point.forward_index),
                    "aft_index": str(point.aft_index),
                }
                for point in envelope.points
            ]
            for envelope in kind.envelopes
        },
    }
    return json.dumps(document, indent=2, sort_keys=False) + "\n"


def load_schedule(path: Path) -> AircraftType:
    """Read a schedule off disk."""
    if not path.exists():
        raise DataError(f"no schedule at {path}")
    return read_schedule(path.read_text(encoding="utf-8"))


def save_schedule(kind: AircraftType, path: Path) -> Path:
    """Write a schedule to disk."""
    path.write_text(write_schedule(kind), encoding="utf-8")
    return path
