import sqlite3
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.errors import DuplicateError, NotFoundError
from holdtrim.model.aircraft import AircraftType, MacGeometry, StructuralLimits
from holdtrim.model.envelope import Envelope, EnvelopePoint
from holdtrim.model.fuel import FuelPoint, FuelTable
from holdtrim.model.hold import CumulativeLimit, HoldLayout
from holdtrim.model.position import Position
from holdtrim.model.trim import TrimPoint, TrimTable
from holdtrim.store import fleet
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened, scalar_int


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def position(
    code: str,
    arm: str,
    accepts: tuple[str, ...] = ("PMC",),
    compartment: str = "MAIN",
) -> Position:
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


def a_type(code: str = "AT7F") -> AircraftType:
    shape = (
        EnvelopePoint(weight=13000, forward_index=Decimal("30.0"), aft_index=Decimal("66.0")),
        EnvelopePoint(weight=20800, forward_index=Decimal("38.0"), aft_index=Decimal("58.0")),
    )
    return AircraftType(
        code=code,
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
                position("11P", "9.400"),
                position("21P", "12.600"),
                position("51", "18.100", accepts=(), compartment="BULK"),
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
                FuelPoint(weight=1000, index=Decimal("-2.4")),
                FuelPoint(weight=2000, index=Decimal("-3.6")),
                FuelPoint(weight=3000, index=Decimal("-2.8")),
                FuelPoint(weight=4500, index=Decimal("1.2")),
            )
        ),
        trim=TrimTable(
            points=(
                TrimPoint(percent_mac=Decimal("15.0"), setting=Decimal("5.5")),
                TrimPoint(percent_mac=Decimal("25.0"), setting=Decimal("3.5")),
                TrimPoint(percent_mac=Decimal("35.0"), setting=Decimal("1.5")),
            )
        ),
        empty_weight=13100,
    )


def test_a_type_goes_in_and_comes_back_whole(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    assert fleet.get_type(conn, "AT7F") == a_type()


def test_the_arms_come_back_as_the_decimals_they_went_in_as(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    read = fleet.get_type(conn, "AT7F")
    assert read.layout.position("11P").arm == Decimal("9.400")
    assert read.geometry.reference_arm == Decimal("12.615")


def test_the_positions_keep_the_order_they_were_registered_in(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    assert fleet.get_type(conn, "AT7F").layout.codes == ("11P", "21P", "51")


def test_a_bulk_position_comes_back_taking_nothing(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    assert fleet.get_type(conn, "AT7F").layout.position("51").bulk


def test_the_cumulative_limits_come_back_with_their_positions(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    limits = fleet.get_type(conn, "AT7F").layout.cumulative
    assert limits[0].positions == ("11P", "21P")


def test_the_fuel_index_table_comes_back(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    read = fleet.get_type(conn, "AT7F")
    assert read.fuel.capacity == 4500
    assert read.fuel.index_at(2000) == Decimal("-3.6")


def test_the_trim_table_comes_back(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    assert fleet.get_type(conn, "AT7F").trim.setting_at(Decimal("25.0")) == Decimal("3.5")


def test_all_three_envelopes_come_back(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    names = [envelope.name for envelope in fleet.get_type(conn, "AT7F").envelopes]
    assert sorted(names) == ["landing", "takeoff", "zero fuel"]


def test_registering_the_same_code_twice_is_refused(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    with pytest.raises(DuplicateError, match="already in the fleet register"):
        fleet.add_type(conn, a_type())


def test_asking_for_a_type_that_is_not_registered(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no type B734 in the fleet"):
        fleet.get_type(conn, "B734")


def test_types_list_in_code_order(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type("AT7F"))
    fleet.add_type(conn, a_type("A306"))
    assert [kind.code for kind in fleet.list_types(conn)] == ["A306", "AT7F"]
    assert fleet.count_types(conn) == 2


def test_removing_a_type_takes_its_layout_with_it(conn: sqlite3.Connection) -> None:
    fleet.add_type(conn, a_type())
    fleet.remove_type(conn, "AT7F")
    assert not fleet.type_exists(conn, "AT7F")
    assert scalar_int(conn, "SELECT count(*) FROM hold_position") == 0
    assert scalar_int(conn, "SELECT count(*) FROM envelope_point") == 0
    assert scalar_int(conn, "SELECT count(*) FROM fuel_point") == 0


def test_removing_a_type_that_is_not_there_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no type B734"):
        fleet.remove_type(conn, "B734")
