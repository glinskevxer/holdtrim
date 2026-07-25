from decimal import Decimal

import pytest

from holdtrim.cargo.reweigh import Correction, check
from holdtrim.errors import DataError


def correction(was: int = 1240, now: int = 1300) -> Correction:
    return Correction(what="125-12345675", was=was, now=now)


def test_a_correction_reports_how_far_it_moved() -> None:
    assert correction().difference == 60
    assert correction().heavier


def test_a_lighter_correction_reads_negative() -> None:
    assert correction(now=1100).difference == -140
    assert not correction(now=1100).heavier


def test_the_share_is_of_what_it_was() -> None:
    assert correction(was=1000, now=1100).share == Decimal("0.100")


def test_a_small_correction_is_not_large() -> None:
    assert not correction().large


def test_a_correction_of_a_third_is_large() -> None:
    assert correction(was=1200, now=1600).large


def test_a_correction_from_nothing_is_refused() -> None:
    with pytest.raises(DataError, match="had no weight to correct"):
        correction(was=0)


def test_a_correction_to_nothing_is_refused() -> None:
    with pytest.raises(DataError, match="corrected to nothing"):
        correction(now=0)


def test_a_correction_describes_itself() -> None:
    assert correction().describe() == "125-12345675 1240 kg became 1300 kg, 60 kg heavier"


def test_a_lighter_correction_says_lighter() -> None:
    assert correction(now=1100).describe().endswith("140 kg lighter")


def test_a_small_correction_is_not_worth_reporting() -> None:
    assert check(correction()) == ()


def test_a_large_correction_is_a_note() -> None:
    found = check(correction(was=1200, now=1600))
    assert found[0].check == "reweigh"
    assert found[0].severity == "watch"
    assert "33.3 percent" in found[0].detail


def test_a_correction_of_more_than_double_stops_the_shipment() -> None:
    found = check(correction(was=500, now=1200))
    assert found[0].severity == "stop"
