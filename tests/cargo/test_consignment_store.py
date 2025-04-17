import sqlite3
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from holdtrim.errors import DuplicateError, NotFoundError
from holdtrim.ids import AirWaybill
from holdtrim.model.consignment import Consignment
from holdtrim.store import consignments
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def consignment(serial: int = 1234567, **changes: object) -> Consignment:
    fields: dict[str, object] = {
        "awb": AirWaybill(prefix="125", serial=serial),
        "origin": "BLL",
        "destination": "LGG",
        "pieces": 8,
        "gross_weight": 1240,
        "volume": Decimal("4.200"),
        "commodity": "machine parts",
        "ready_on": date(2025, 5, 12),
        "handling": ("PER",),
    }
    fields.update(changes)
    return Consignment(**fields)  # type: ignore[arg-type]


def test_a_waybill_goes_on_file_and_comes_back(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment())
    assert consignments.get(conn, "125-12345675") == consignment()


def test_the_volume_comes_back_as_the_decimal_it_went_in_as(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment())
    assert consignments.get(conn, "12512345675").volume == Decimal("4.200")


def test_the_handling_codes_survive_the_round_trip(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment(handling=("PER", "EAT")))
    assert consignments.get(conn, "125-12345675").handling == ("EAT", "PER")


def test_a_waybill_with_no_codes_comes_back_with_none(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment(handling=()))
    assert consignments.get(conn, "125-12345675").handling == ()


def test_the_same_waybill_twice_is_refused(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment())
    with pytest.raises(DuplicateError, match="already on file"):
        consignments.add(conn, consignment())


def test_asking_for_a_waybill_that_is_not_on_file(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no waybill 12500000000 on file"):
        consignments.get(conn, "125-00000000")


def test_waybills_list_in_number_order(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment(2000004))
    consignments.add(conn, consignment(1000006))
    numbers = [c.awb.serial for c in consignments.listing(conn)]
    assert numbers == [1000006, 2000004]
    assert consignments.count(conn) == 2


def test_a_sector_lists_oldest_ready_first(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment(1000006, ready_on=date(2025, 5, 14)))
    consignments.add(conn, consignment(2000004, ready_on=date(2025, 5, 11)))
    found = consignments.on_route(conn, "bll", "lgg")
    assert [c.ready_on.day for c in found] == [11, 14]


def test_another_sector_does_not_show(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment())
    assert consignments.on_route(conn, "BLL", "CDG") == []


def test_only_what_is_ready_by_the_day_comes_back(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment(1000006, ready_on=date(2025, 5, 11)))
    consignments.add(conn, consignment(2000004, ready_on=date(2025, 5, 14)))
    ready = consignments.ready_by(conn, "BLL", "LGG", date(2025, 5, 12))
    assert [c.awb.serial for c in ready] == [1000006]


def test_the_tonnage_over_a_sector_adds_up(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment(1000006, gross_weight=1240))
    consignments.add(conn, consignment(2000004, gross_weight=760))
    assert consignments.tonnage(conn, "BLL", "LGG") == 2000


def test_a_sector_with_nothing_booked_weighs_nothing(conn: sqlite3.Connection) -> None:
    assert consignments.tonnage(conn, "BLL", "CDG") == 0


def test_saving_overwrites_the_row(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment())
    consignments.save(conn, consignment(gross_weight=1300))
    assert consignments.get(conn, "125-12345675").gross_weight == 1300


def test_saving_something_that_was_never_filed_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no waybill"):
        consignments.save(conn, consignment())


def test_removing_takes_it_off_file(conn: sqlite3.Connection) -> None:
    consignments.add(conn, consignment())
    consignments.remove(conn, "125-12345675")
    assert not consignments.exists(conn, "125-12345675")


def test_removing_something_that_is_not_there_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no waybill"):
        consignments.remove(conn, "125-12345675")
