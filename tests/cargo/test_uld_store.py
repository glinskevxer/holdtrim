import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from holdtrim.errors import DuplicateError, NotFoundError
from holdtrim.model.uld import Uld, uld
from holdtrim.store import ulds
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def device(code: str = "PMC12345QH", **changes: object) -> Uld:
    fields: dict[str, object] = {
        "code": code,
        "tare": 110,
        "max_gross": 4626,
        "at_station": "BLL",
    }
    fields.update(changes)
    return uld(**fields)  # type: ignore[arg-type]


def test_a_device_goes_on_and_comes_back(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device())
    assert ulds.get(conn, "PMC12345QH") == device()


def test_the_owner_code_survives_the_round_trip(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device())
    assert ulds.get(conn, "PMC12345QH").code.owner == "QH"


def test_the_same_device_twice_is_refused(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device())
    with pytest.raises(DuplicateError, match="already on the ULD register"):
        ulds.add(conn, device())


def test_asking_for_a_device_that_is_not_registered(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no ULD AKE99999QH"):
        ulds.get(conn, "AKE99999QH")


def test_devices_list_in_code_order(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device("PMC12345QH"))
    ulds.add(conn, device("AKE10001QH", tare=68, max_gross=1588))
    assert [d.code.formatted() for d in ulds.listing(conn)] == ["AKE10001QH", "PMC12345QH"]
    assert ulds.count(conn) == 2


def test_the_devices_at_a_station_come_back(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device("PMC12345QH"))
    ulds.add(conn, device("PMC12346QH", at_station="LGG"))
    assert [d.code.serial for d in ulds.at_station(conn, "bll")] == ["12345"]


def test_a_station_can_be_narrowed_to_one_base(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device("PMC12345QH"))
    ulds.add(conn, device("AKE10001QH", tare=68, max_gross=1588))
    assert [d.base for d in ulds.at_station(conn, "BLL", base="ake")] == ["AKE"]


def test_a_station_can_be_narrowed_to_serviceable_devices(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device("PMC12345QH"))
    ulds.add(conn, device("PMC12346QH", condition="damaged"))
    found = ulds.at_station(conn, "BLL", serviceable_only=True)
    assert [d.code.serial for d in found] == ["12345"]


def test_devices_with_no_station_are_in_transit(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device("PMC12345QH", at_station=""))
    ulds.add(conn, device("PMC12346QH"))
    assert [d.code.serial for d in ulds.in_transit(conn)] == ["12345"]


def test_the_stock_at_a_station_counts_by_base(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device("PMC12345QH"))
    ulds.add(conn, device("PMC12346QH"))
    ulds.add(conn, device("AKE10001QH", tare=68, max_gross=1588))
    assert ulds.stock(conn, "BLL") == {"AKE": 1, "PMC": 2}


def test_a_station_holding_nothing_has_no_stock(conn: sqlite3.Connection) -> None:
    assert ulds.stock(conn, "CDG") == {}


def test_a_device_moves_to_another_station(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device())
    ulds.move(conn, "PMC12345QH", "LGG")
    assert ulds.get(conn, "PMC12345QH").at_station == "LGG"


def test_saving_records_a_change_of_condition(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device())
    ulds.save(conn, device(condition="damaged"))
    assert not ulds.get(conn, "PMC12345QH").loadable


def test_saving_a_device_that_was_never_registered_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no ULD"):
        ulds.save(conn, device())


def test_removing_takes_it_off(conn: sqlite3.Connection) -> None:
    ulds.add(conn, device())
    ulds.remove(conn, "PMC12345QH")
    assert not ulds.exists(conn, "PMC12345QH")


def test_removing_one_that_is_not_there_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no ULD"):
        ulds.remove(conn, "PMC12345QH")
