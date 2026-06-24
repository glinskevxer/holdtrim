import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from holdtrim.model.movement import movement
from holdtrim.model.uld import uld
from holdtrim.report import uldflow
from holdtrim.report.uldflow import Flow, Idle
from holdtrim.store import movements, ulds
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def moved(
    conn: sqlite3.Connection,
    station: str,
    direction: str,
    day: date,
    code: str = "PMC12345QH",
) -> None:
    movements.record(conn, movement(day=day, station=station, uld=code, direction=direction))


def test_a_flow_reports_what_it_is_up_or_down() -> None:
    assert Flow(station="BLL", arrived=4, left=1).net == 3
    assert Flow(station="BLL", arrived=4, left=1).gaining
    assert not Flow(station="BLL", arrived=1, left=4).gaining


def test_a_flow_describes_itself() -> None:
    assert Flow(station="BLL", arrived=4, left=1).describe() == "BLL in 4, out 1, net +3"


def test_the_flows_count_both_directions(conn: sqlite3.Connection) -> None:
    moved(conn, "BLL", "out", date(2025, 5, 12))
    moved(conn, "LGG", "in", date(2025, 5, 12))
    moved(conn, "LGG", "in", date(2025, 5, 13), code="PMC12346QH")
    report = uldflow.flows(conn, date(2025, 5, 12), date(2025, 5, 13))
    assert [flow.station for flow in report] == ["BLL", "LGG"]
    assert report[1].arrived == 2


def test_a_movement_outside_the_period_is_left_out(conn: sqlite3.Connection) -> None:
    moved(conn, "BLL", "out", date(2025, 5, 1))
    assert uldflow.flows(conn, date(2025, 5, 12), date(2025, 5, 13)) == ()


def test_the_busiest_station_is_the_one_that_handled_most(conn: sqlite3.Connection) -> None:
    moved(conn, "BLL", "out", date(2025, 5, 12))
    moved(conn, "LGG", "in", date(2025, 5, 12))
    moved(conn, "LGG", "out", date(2025, 5, 13))
    report = uldflow.flows(conn, date(2025, 5, 12), date(2025, 5, 13))
    assert uldflow.busiest(report) == "LGG"


def test_nothing_moving_has_no_busiest_station() -> None:
    assert uldflow.busiest(()) == ""


def test_the_stations_piling_up_come_back_most_first(conn: sqlite3.Connection) -> None:
    moved(conn, "LGG", "in", date(2025, 5, 12))
    moved(conn, "LGG", "in", date(2025, 5, 12), code="PMC12346QH")
    moved(conn, "BLL", "in", date(2025, 5, 12), code="PMC12347QH")
    moved(conn, "BLL", "out", date(2025, 5, 12), code="PMC12348QH")
    report = uldflow.flows(conn, date(2025, 5, 12), date(2025, 5, 13))
    assert [flow.station for flow in uldflow.piling_up(report)] == ["LGG"]


def test_a_device_standing_too_long_is_idle(conn: sqlite3.Connection) -> None:
    ulds.add(conn, uld(code="PMC12345QH", tare=110, max_gross=4626, at_station="LGG"))
    moved(conn, "LGG", "in", date(2025, 5, 1))
    found = uldflow.idle(conn, date(2025, 5, 20))
    assert found[0].uld == "PMC12345QH"
    assert found[0].days == 19


def test_a_device_that_arrived_yesterday_is_not_idle(conn: sqlite3.Connection) -> None:
    ulds.add(conn, uld(code="PMC12345QH", tare=110, max_gross=4626, at_station="LGG"))
    moved(conn, "LGG", "in", date(2025, 5, 19))
    assert uldflow.idle(conn, date(2025, 5, 20)) == ()


def test_a_device_in_transit_is_not_standing_anywhere(conn: sqlite3.Connection) -> None:
    ulds.add(conn, uld(code="PMC12345QH", tare=110, max_gross=4626))
    moved(conn, "LGG", "in", date(2025, 5, 1))
    assert uldflow.idle(conn, date(2025, 5, 20)) == ()


def test_a_device_with_no_arrival_logged_is_left_out(conn: sqlite3.Connection) -> None:
    ulds.add(conn, uld(code="PMC12345QH", tare=110, max_gross=4626, at_station="LGG"))
    assert uldflow.idle(conn, date(2025, 5, 20)) == ()


def test_an_idle_entry_describes_itself() -> None:
    entry = Idle(uld="PMC12345QH", station="LGG", since=date(2025, 5, 1), days=19)
    assert entry.describe() == "PMC12345QH at LGG since 2025-05-01, 19 day(s)"
