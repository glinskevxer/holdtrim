import sqlite3
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.errors import DuplicateError, NotFoundError
from holdtrim.model.aircraft import AircraftType, MacGeometry, StructuralLimits
from holdtrim.model.envelope import Envelope, EnvelopePoint
from holdtrim.model.hold import CumulativeLimit, HoldLayout
from holdtrim.model.position import Position
from holdtrim.store import fleet
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened, scalar_int


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def position(code: str, arm: str, accepts: tuple[str, ...] = ("PMC",)) -> Position:
    return Position(
        code=code,
        compartment="MAIN",
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
        EnvelopePoint(weight=13000, forward_index=Decimal("38.0"), aft_index=Decimal("62.0")),
        EnvelopePoint(weight=20800, forward_index=Decimal("46.0"), aft_index=Decimal("57.0")),
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
                position("51", "18.100", accepts=()),
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


def test_removing_a_type_that_is_not_there_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no type B734"):
        fleet.remove_type(conn, "B734")
