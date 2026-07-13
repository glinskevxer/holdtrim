import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.ids import AirWaybill
from holdtrim.model.consignment import Consignment
from holdtrim.model.movement import movement
from holdtrim.model.uld import uld
from holdtrim.store import consignments, doctor, movements, settings, ulds
from holdtrim.store.doctor import Complaint
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def test_a_fresh_book_has_nothing_wrong_with_it(conn: sqlite3.Connection) -> None:
    complaints = doctor.examine(conn)
    assert complaints == ()
    assert doctor.sound(complaints)


def test_a_complaint_describes_itself() -> None:
    assert Complaint(about="schema", detail="behind").describe() == "schema: behind"


def test_a_book_behind_the_schema_is_complained_about(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM schema_migration WHERE version > 2")
    complaints = doctor.schema(conn)
    assert "have not been applied" in complaints[0].detail


def test_a_movement_for_an_unregistered_device_is_found(conn: sqlite3.Connection) -> None:
    movements.record(
        conn, movement(day=date(2025, 5, 12), station="BLL", uld="PMC12345QH", direction="in")
    )
    complaints = doctor.orphan_movements(conn)
    assert "not on the ULD register" in complaints[0].detail


def test_a_movement_for_a_registered_device_is_not(conn: sqlite3.Connection) -> None:
    ulds.add(conn, uld(code="PMC12345QH", tare=110, max_gross=4626, at_station="BLL"))
    movements.record(
        conn, movement(day=date(2025, 5, 12), station="BLL", uld="PMC12345QH", direction="in")
    )
    assert doctor.orphan_movements(conn) == []


def test_a_handling_code_this_build_does_not_know_is_found(conn: sqlite3.Connection) -> None:
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
            ready_on=date(2025, 5, 12),
            handling=("ZZZ",),
        ),
    )
    complaints = doctor.unknown_codes(conn)
    assert "carries ZZZ" in complaints[0].detail


def test_a_setting_that_stopped_being_a_number_is_found(conn: sqlite3.Connection) -> None:
    settings.put(conn, "lmc.tolerance", "500")
    conn.execute("UPDATE setting SET value = 'plenty' WHERE name = 'lmc.tolerance'")
    complaints = doctor.unreadable_settings(conn)
    assert "lmc.tolerance" in complaints[0].detail


def test_a_setting_left_at_its_default_is_not_examined(conn: sqlite3.Connection) -> None:
    assert doctor.unreadable_settings(conn) == []


def test_a_dangling_reference_is_found(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("INSERT INTO load_plan (flight_key, edition) VALUES ('QH999/2025-05-12', 1)")
    conn.execute("PRAGMA foreign_keys = ON")
    complaints = doctor.file_itself(conn)
    assert complaints[0].about == "references"


def test_everything_runs_in_one_examination(conn: sqlite3.Connection) -> None:
    movements.record(
        conn, movement(day=date(2025, 5, 12), station="BLL", uld="PMC12345QH", direction="in")
    )
    complaints = doctor.examine(conn)
    assert not doctor.sound(complaints)
    assert any(complaint.about == "orphan" for complaint in complaints)
