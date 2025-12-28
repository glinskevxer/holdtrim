import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from holdtrim.store import consignments, importer
from holdtrim.store.importer import Outcome, Rejected
from holdtrim.store.migrations import apply
from holdtrim.store.sqlite import opened

HEADER = "awb,origin,destination,pieces,gross_weight,volume,commodity,ready_on,handling"
GOOD = f"{HEADER}\n125-12345675,BLL,LGG,8,1240,4.2,machine parts,2025-05-12,PER\n"


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with opened(tmp_path / "book.sqlite3") as connection:
        apply(connection)
        yield connection


def test_a_good_file_reads_clean() -> None:
    outcome = importer.read(GOOD)
    assert outcome.clean
    assert outcome.accepted[0].awb.serial == 1234567
    assert outcome.accepted[0].handling == ("PER",)


def test_the_outcome_totals_the_weight() -> None:
    assert importer.read(GOOD).weight == 1240


def test_the_outcome_describes_itself() -> None:
    assert importer.read(GOOD).describe() == "1 accepted, 0 rejected, 1240 kg"


def test_a_file_with_a_missing_column_is_reported_on_line_one() -> None:
    outcome = importer.read("awb,origin\n125-12345675,BLL\n")
    assert outcome.rejected[0].line == 1
    assert "no destination" in outcome.rejected[0].reason


def test_a_bad_check_digit_is_reported_with_its_line() -> None:
    text = f"{HEADER}\n125-12345674,BLL,LGG,8,1240,4.2,parts,2025-05-12,\n"
    outcome = importer.read(text)
    assert outcome.rejected[0].line == 2
    assert "check digit" in outcome.rejected[0].reason


def test_an_unknown_handling_code_is_reported() -> None:
    text = f"{HEADER}\n125-12345675,BLL,LGG,8,1240,4.2,parts,2025-05-12,ZZZ\n"
    assert "nobody knows" in importer.read(text).rejected[0].reason


def test_a_bad_date_is_reported() -> None:
    text = f"{HEADER}\n125-12345675,BLL,LGG,8,1240,4.2,parts,the twelfth,\n"
    assert importer.read(text).rejected[0].line == 2


def test_a_bad_weight_is_reported() -> None:
    text = f"{HEADER}\n125-12345675,BLL,LGG,8,heavy,4.2,parts,2025-05-12,\n"
    assert importer.read(text).rejected[0].line == 2


def test_one_bad_row_does_not_stop_the_good_ones() -> None:
    text = (
        f"{HEADER}\n"
        "125-12345674,BLL,LGG,8,1240,4.2,parts,2025-05-12,\n"
        "125-20000046,BLL,LGG,4,760,2.1,spares,2025-05-12,\n"
    )
    outcome = importer.read(text)
    assert len(outcome.accepted) == 1
    assert len(outcome.rejected) == 1
    assert not outcome.clean


def test_a_rejected_row_describes_itself() -> None:
    assert Rejected(line=4, reason="no good").describe() == "line 4: no good"


def test_loading_puts_the_rows_on_file(conn: sqlite3.Connection) -> None:
    outcome = importer.load(conn, GOOD)
    assert outcome.clean
    assert consignments.count(conn) == 1


def test_loading_the_same_file_twice_rejects_the_repeats(conn: sqlite3.Connection) -> None:
    importer.load(conn, GOOD)
    outcome = importer.load(conn, GOOD)
    assert consignments.count(conn) == 1
    assert "already on file" in outcome.rejected[0].reason


def test_an_empty_outcome_is_clean() -> None:
    assert Outcome().clean
    assert Outcome().weight == 0
