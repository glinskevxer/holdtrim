import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.errors import NotFoundError, StateError
from holdtrim.ids import AirWaybill
from holdtrim.model.consignment import Consignment
from holdtrim.model.danger import DangerousGoods
from holdtrim.store import consignments, dangerous
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened

AWB = "125-12345675"


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        consignments.add(
            connection,
            Consignment(
                awb=AirWaybill(prefix="125", serial=1234567),
                origin="BLL",
                destination="LGG",
                pieces=4,
                gross_weight=400,
                volume=Decimal("1.200"),
                commodity="paint",
                ready_on=date(2025, 5, 12),
                handling=("RFL",),
            ),
        )
        yield connection


def entry(**changes: object) -> DangerousGoods:
    fields: dict[str, object] = {
        "un_number": 1263,
        "proper_shipping_name": "Paint",
        "hazard_class": "3",
        "packages": 4,
        "net_quantity": Decimal("5.000"),
        "unit": "L",
        "packing_group": "II",
        "packing_instruction": "364",
    }
    fields.update(changes)
    return DangerousGoods(**fields)  # type: ignore[arg-type]


def test_a_line_goes_in_and_comes_back(conn: sqlite3.Connection) -> None:
    dangerous.declare(conn, AWB, entry())
    assert dangerous.against(conn, AWB) == (entry(),)


def test_the_subsidiary_risks_survive_the_round_trip(conn: sqlite3.Connection) -> None:
    dangerous.declare(conn, AWB, entry(subsidiary_risks=("8",)))
    assert dangerous.against(conn, AWB)[0].subsidiary_risks == ("8",)


def test_a_line_with_no_risks_comes_back_with_none(conn: sqlite3.Connection) -> None:
    dangerous.declare(conn, AWB, entry())
    assert dangerous.against(conn, AWB)[0].subsidiary_risks == ()


def test_a_transport_index_survives_the_round_trip(conn: sqlite3.Connection) -> None:
    hot = entry(hazard_class="7", packing_group="", transport_index=Decimal("0.4"), unit="TBq")
    dangerous.declare(conn, AWB, hot)
    assert dangerous.against(conn, AWB)[0].transport_index == Decimal("0.4")


def test_a_line_with_no_index_comes_back_with_none(conn: sqlite3.Connection) -> None:
    dangerous.declare(conn, AWB, entry())
    assert dangerous.against(conn, AWB)[0].transport_index is None


def test_the_cargo_only_flag_survives(conn: sqlite3.Connection) -> None:
    dangerous.declare(conn, AWB, entry(cargo_aircraft_only=True))
    assert dangerous.against(conn, AWB)[0].cargo_aircraft_only


def test_several_lines_keep_the_order_they_were_declared(conn: sqlite3.Connection) -> None:
    dangerous.declare(conn, AWB, entry(un_number=1263))
    dangerous.declare(conn, AWB, entry(un_number=1993, proper_shipping_name="Flammable liquid"))
    assert [line.un_number for line in dangerous.against(conn, AWB)] == [1263, 1993]


def test_declaring_against_a_waybill_that_is_not_on_file(conn: sqlite3.Connection) -> None:
    with pytest.raises(StateError, match="is not on file"):
        dangerous.declare(conn, "125-20000046", entry())


def test_a_waybill_with_nothing_declared_has_nothing(conn: sqlite3.Connection) -> None:
    assert dangerous.against(conn, AWB) == ()


def test_the_waybills_with_declarations_come_back(conn: sqlite3.Connection) -> None:
    dangerous.declare(conn, AWB, entry())
    assert dangerous.waybills(conn) == ["12512345675"]
    assert dangerous.count(conn) == 1


def test_clearing_takes_every_line_off(conn: sqlite3.Connection) -> None:
    dangerous.declare(conn, AWB, entry())
    dangerous.declare(conn, AWB, entry(un_number=1993))
    assert dangerous.clear(conn, AWB) == 2
    assert dangerous.against(conn, AWB) == ()


def test_clearing_a_waybill_with_nothing_on_it_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="nothing is declared"):
        dangerous.clear(conn, AWB)
