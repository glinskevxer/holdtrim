"""One flight, end to end, against a book made and thrown away.

This is what CI runs against the installed wheel. It is not a substitute for
the test suite; it answers a different question, which is whether the thing
that was packaged works at all when it is imported the way a user imports it.

It builds a small aeroplane, files a flight, plans it, checks it, issues the
loadsheet and sends the two messages. If any of that raises, the package is
broken in a way no unit test would necessarily notice.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from holdtrim.ids import Flight
from holdtrim.message import cpm, ldm
from holdtrim.model.aircraft import AircraftType, MacGeometry, StructuralLimits
from holdtrim.model.envelope import Envelope, EnvelopePoint
from holdtrim.model.flight import Sector
from holdtrim.model.fuel import FuelPoint, FuelTable
from holdtrim.model.hold import CumulativeLimit, HoldLayout
from holdtrim.model.position import Position
from holdtrim.model.station import Station
from holdtrim.model.tail import Tail
from holdtrim.model.trim import TrimPoint, TrimTable
from holdtrim.office import read
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.store import fleet, flights, plans, stations
from holdtrim.store.book import open_book

DAY = date(2025, 5, 12)
KEY = "QH412/2025-05-12"


def _position(code: str, arm: str, compartment: str, accepts: tuple[str, ...]) -> Position:
    return Position(
        code=code,
        compartment=compartment,
        arm=Decimal(arm),
        max_weight=3175,
        length=Decimal("3.175"),
        width=Decimal("2.235"),
        max_running_load=1200,
        max_area_load=732,
        accepts=accepts,
    )


def example_type() -> AircraftType:
    """A small freighter, enough to exercise every part of the calculation."""
    shape = (
        EnvelopePoint(weight=13000, forward_index=Decimal("30.0"), aft_index=Decimal("66.0")),
        EnvelopePoint(weight=20800, forward_index=Decimal("38.0"), aft_index=Decimal("58.0")),
    )
    return AircraftType(
        code="AT7F",
        name="ATR 72 freighter",
        limits=StructuralLimits(
            max_ramp=23050, max_takeoff=22800, max_landing=22350, max_zero_fuel=20800
        ),
        geometry=MacGeometry(
            reference_arm=Decimal("12.615"),
            lemac=Decimal("11.409"),
            mac_length=Decimal("2.303"),
            index_constant=Decimal("1000"),
            index_reference=Decimal("50"),
        ),
        layout=HoldLayout(
            positions=(
                _position("11P", "9.400", "MAIN", ("PMC",)),
                _position("21P", "12.600", "MAIN", ("PMC",)),
                _position("51", "18.100", "BULK", ()),
            ),
            cumulative=(
                CumulativeLimit(label="11P and 21P", positions=("11P", "21P"), max_weight=5400),
            ),
        ),
        envelopes=(
            Envelope(name="zero fuel", points=shape),
            Envelope(name="takeoff", points=shape),
            Envelope(name="landing", points=shape),
        ),
        fuel=FuelTable(
            points=(
                FuelPoint(weight=0, index=Decimal("0.0")),
                FuelPoint(weight=2000, index=Decimal("-3.6")),
                FuelPoint(weight=4500, index=Decimal("1.2")),
            )
        ),
        trim=TrimTable(
            points=(
                TrimPoint(percent_mac=Decimal("15.0"), setting=Decimal("5.5")),
                TrimPoint(percent_mac=Decimal("35.0"), setting=Decimal("1.5")),
                TrimPoint(percent_mac=Decimal("45.0"), setting=Decimal("-0.5")),
            )
        ),
        empty_weight=13100,
    )


def run(path: Path, *, quiet: bool = False) -> str:
    """Work one flight all the way through and give back its summary line."""
    with open_book(path, create=True) as book:
        connection = book.connection
        stations.add(connection, Station(code="BLL", name="Billund", elevation_feet=247))
        stations.add(connection, Station(code="LGG", name="Liege", elevation_feet=659))
        fleet.add_type(connection, example_type())
        fleet.add_tail(
            connection,
            Tail(
                registration="OY-JAF",
                type_code="AT7F",
                dry_operating_weight=13640,
                dry_operating_index=Decimal("46.2"),
                weighed_on=date(2024, 6, 18),
            ),
        )
        flights.add(
            connection,
            Sector(
                designator=Flight(carrier="QH", number=412),
                day=DAY,
                registration="OY-JAF",
                origin="BLL",
                destination="LGG",
                taxi_fuel=90,
                trip_fuel=1450,
                takeoff_fuel=2600,
            ),
        )
        plans.save(
            connection,
            LoadPlan(
                flight_key=KEY,
                assignments=(
                    Assignment(position="11P", weight=2000, uld="PMC12345QH", destination="LGG"),
                    Assignment(position="51", weight=300, destination="LGG"),
                ),
            ),
        )
        file = read(connection, KEY)
        file.check_flyable()
        sheet = file.loadsheet("smoke test").issue()
        wire = {"addresses": ("LGGKLQH",), "origin": "BLLLDQH", "filed": "121815"}
        ldm.build(sheet, **wire).render()  # type: ignore[arg-type]
        cpm.build(sheet, **wire).render()  # type: ignore[arg-type]
    if not quiet:
        print(sheet.summary())
    return sheet.summary()


def main(argv: list[str] | None = None) -> int:
    """Run the smoke test against a temporary book."""
    parser = argparse.ArgumentParser(description="Work one flight end to end.")
    parser.add_argument("--quiet", action="store_true")
    arguments = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as where:
        run(Path(where) / "smoke.sqlite3", quiet=arguments.quiet)
    if not arguments.quiet:
        print("smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
