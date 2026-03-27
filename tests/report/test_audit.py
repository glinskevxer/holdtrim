import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.ids import Flight
from holdtrim.model.flight import Sector
from holdtrim.model.movement import movement
from holdtrim.model.tail import Tail
from holdtrim.plan.loadplan import Assignment, LoadPlan
from holdtrim.report import audit
from holdtrim.store import fleet, flights, movements, plans, sheets
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened
from tests.fleet.test_type_store import a_type

KEY = "QH412/2025-05-12"
DAY = date(2025, 5, 12)


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
        yield connection


def planned(conn: sqlite3.Connection, weight: int = 2000) -> None:
    plans.save(
        conn,
        LoadPlan(
            flight_key=KEY,
            assignments=(
                Assignment(position="11P", weight=weight, uld="PMC12345QH", destination="LGG"),
            ),
        ),
    )


def issue(conn: sqlite3.Connection, payload: int = 2000) -> None:
    from holdtrim.office import read

    file = read(conn, KEY)
    sheets.record(conn, sheets.from_sheet(file.loadsheet("K Ravn"), DAY))
    assert payload


def test_a_trail_gathers_the_flight_file(conn: sqlite3.Connection) -> None:
    trail = audit.gather(conn, KEY)
    assert trail.key == KEY
    assert not trail.signed
    assert trail.editions == 0


def test_an_unplanned_flight_says_nothing_is_planned(conn: sqlite3.Connection) -> None:
    assert "nothing is planned" in audit.render(audit.gather(conn, KEY))


def test_the_plan_prints_position_by_position(conn: sqlite3.Connection) -> None:
    planned(conn)
    printed = audit.render(audit.gather(conn, KEY))
    assert "11P PMC12345QH 2000 kg" in printed
    assert "payload 2000 kg over 1 position(s)" in printed


def test_the_checks_print_under_the_plan(conn: sqlite3.Connection) -> None:
    planned(conn)
    assert "every check passes" in audit.render(audit.gather(conn, KEY))


def test_a_broken_plan_prints_its_findings(conn: sqlite3.Connection) -> None:
    planned(conn, weight=3400)
    assert "position 11P" in audit.render(audit.gather(conn, KEY))


def test_a_flight_with_no_loadsheet_says_none(conn: sqlite3.Connection) -> None:
    planned(conn)
    printed = audit.render(audit.gather(conn, KEY))
    assert "LOADSHEETS ISSUED" in printed
    assert "none" in printed


def test_an_issued_sheet_prints_in_the_trail(conn: sqlite3.Connection) -> None:
    planned(conn)
    issue(conn)
    trail = audit.gather(conn, KEY)
    assert trail.signed
    assert trail.editions == 1
    assert "edition 1 issued 2025-05-12 by K Ravn" in audit.render(trail)


def test_a_plan_changed_after_issue_is_flagged(conn: sqlite3.Connection) -> None:
    planned(conn)
    issue(conn)
    planned(conn, weight=2400)
    trail = audit.gather(conn, KEY)
    assert trail.disagrees
    assert "the plan now carries 2400 kg" in audit.render(trail)


def test_a_plan_that_has_not_changed_is_not_flagged(conn: sqlite3.Connection) -> None:
    planned(conn)
    issue(conn)
    assert not audit.gather(conn, KEY).disagrees


def test_the_movements_on_this_flight_print(conn: sqlite3.Connection) -> None:
    movements.record(
        conn,
        movement(day=DAY, station="BLL", uld="PMC12345QH", direction="out", flight_key=KEY),
    )
    movements.record(conn, movement(day=DAY, station="BLL", uld="PMC12346QH", direction="in"))
    printed = audit.render(audit.gather(conn, KEY))
    assert "PMC12345QH" in printed
    assert "PMC12346QH" not in printed


def test_the_weighing_dates_print(conn: sqlite3.Connection) -> None:
    printed = audit.render(audit.gather(conn, KEY))
    assert "weighed 2024-06-18" in printed
    assert "expires 2029-06-18" in printed
