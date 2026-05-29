import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.ids import AirWaybill, Flight
from holdtrim.model.consignment import Consignment
from holdtrim.model.flight import Sector
from holdtrim.model.movement import movement
from holdtrim.model.tail import Tail
from holdtrim.model.uld import uld
from holdtrim.office import read
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.report import handover
from holdtrim.report.handover import Handover
from holdtrim.store import consignments, fleet, flights, movements, plans, sheets, ulds
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened
from tests.fleet.test_type_store import a_type

DAY = date(2025, 5, 12)
KEY = "QH412/2025-05-12"


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        fleet.add_type(connection, a_type())
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
        yield connection


def fly(conn: sqlite3.Connection, status: str = "planned", number: int = 412) -> str:
    flights.add(
        conn,
        Sector(
            designator=Flight(carrier="QH", number=number),
            day=DAY,
            registration="OY-JAF",
            origin="BLL",
            destination="LGG",
            taxi_fuel=90,
            trip_fuel=1450,
            takeoff_fuel=2600,
            status=status,
        ),
    )
    return f"QH{number}/{DAY.isoformat()}"


def plan_it(conn: sqlite3.Connection, key: str) -> None:
    plans.save(
        conn,
        LoadPlan(
            flight_key=key,
            assignments=(Assignment(position="11P", weight=2000, destination="LGG"),),
        ),
    )


def test_an_empty_station_hands_over_nothing(conn: sqlite3.Connection) -> None:
    sheet = handover.gather(conn, "BLL", DAY)
    assert sheet.quiet
    assert "nothing to hand over" in handover.render(sheet)


def test_an_open_flight_is_handed_over(conn: sqlite3.Connection) -> None:
    fly(conn)
    sheet = handover.gather(conn, "bll", DAY)
    assert sheet.open_flights == ("QH412/12",)
    assert "flights still open" in handover.render(sheet)


def test_an_open_flight_with_no_plan_is_handed_over(conn: sqlite3.Connection) -> None:
    fly(conn)
    assert handover.gather(conn, "BLL", DAY).unplanned == ("QH412/12",)


def test_an_open_flight_with_a_plan_is_not(conn: sqlite3.Connection) -> None:
    plan_it(conn, fly(conn))
    assert handover.gather(conn, "BLL", DAY).unplanned == ()


def test_a_closed_flight_with_no_loadsheet_is_handed_over(conn: sqlite3.Connection) -> None:
    fly(conn, status="closed")
    assert handover.gather(conn, "BLL", DAY).unsigned == ("QH412/12",)


def test_a_closed_flight_with_a_loadsheet_is_not(conn: sqlite3.Connection) -> None:
    key = fly(conn, status="closed")
    plan_it(conn, key)
    sheets.record(conn, sheets.from_sheet(read(conn, key).loadsheet("K Ravn"), DAY))
    assert handover.gather(conn, "BLL", DAY).unsigned == ()


def test_a_weighing_running_out_is_handed_over(conn: sqlite3.Connection) -> None:
    sheet = handover.gather(conn, "BLL", date(2029, 5, 20))
    assert sheet.weighings
    assert "OY-JAF expires 2029-06-18" in sheet.weighings[0]


def test_a_device_past_its_free_days_is_handed_over(conn: sqlite3.Connection) -> None:
    ulds.add(conn, uld(code="PMC12345QH", tare=110, max_gross=4626, at_station="BLL"))
    movements.record(
        conn,
        movement(day=date(2025, 5, 1), station="BLL", uld="PMC12345QH", direction="in"),
    )
    assert handover.gather(conn, "BLL", DAY).chargeable


def test_cargo_ready_on_a_sector_that_flies_is_handed_over(conn: sqlite3.Connection) -> None:
    fly(conn)
    consignments.add(
        conn,
        Consignment(
            awb=AirWaybill(prefix="125", serial=1234567),
            origin="BLL",
            destination="LGG",
            pieces=4,
            gross_weight=400,
            volume=Decimal("1.200"),
            commodity="parts",
            ready_on=date(2025, 5, 11),
        ),
    )
    sheet = handover.gather(conn, "BLL", DAY)
    assert sheet.waiting
    assert "125-12345675 400 kg for LGG" in sheet.waiting[0]


def test_another_station_hands_over_nothing_of_ours(conn: sqlite3.Connection) -> None:
    fly(conn)
    assert handover.gather(conn, "LGG", DAY).open_flights == ()


def test_a_handover_with_something_on_it_is_not_quiet() -> None:
    sheet = Handover(
        day=DAY,
        station="BLL",
        open_flights=("QH412/12",),
        unsigned=(),
        unplanned=(),
        weighings=(),
        chargeable=(),
        waiting=(),
    )
    assert not sheet.quiet
