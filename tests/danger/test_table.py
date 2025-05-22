from decimal import Decimal

import pytest

from holdtrim.danger.table import (
    CLASS_NAMES,
    SEGREGATE,
    SEGREGATED_PAIRS,
    class_name,
    conflicts,
    is_explosive_exception,
    must_segregate,
    normalise,
    separation_for,
)
from holdtrim.errors import DataError


def test_a_class_reads_back_its_name() -> None:
    assert class_name("5.1") == "oxidiser"
    assert class_name("  8 ") == "corrosive"


def test_a_class_outside_the_table_is_refused() -> None:
    with pytest.raises(DataError, match="not a class this table covers"):
        class_name("11")


def test_an_explosive_division_reads_as_class_one() -> None:
    assert normalise("1.4G") == "1"
    assert class_name("1.4G") == "explosives"


def test_a_division_that_is_not_explosive_keeps_its_division() -> None:
    assert normalise("5.1") == "5.1"


def test_flammable_liquid_and_oxidiser_are_kept_apart() -> None:
    assert must_segregate("3", "5.1")


def test_every_pair_is_listed_once_in_the_source_table() -> None:
    listed = [tuple(sorted(pair)) for pair in SEGREGATED_PAIRS]
    assert len(set(listed)) == len(listed)


def test_the_table_reads_the_same_both_ways() -> None:
    for hazard, against in SEGREGATE.items():
        for other in against:
            assert must_segregate(hazard, other)
            assert must_segregate(other, hazard)


def test_every_class_in_the_segregation_table_has_a_name() -> None:
    for hazard, against in SEGREGATE.items():
        assert hazard in CLASS_NAMES
        for other in against:
            assert other in CLASS_NAMES


def test_two_classes_with_no_entry_travel_together() -> None:
    assert not must_segregate("3", "9")
    assert not must_segregate("2.2", "6.1")


def test_a_class_does_not_segregate_from_itself() -> None:
    assert not must_segregate("3", "3")


def test_explosives_are_kept_from_everything() -> None:
    assert must_segregate("1.4G", "9")
    assert must_segregate("9", "1.4G")


def test_the_one_four_s_exception_travels_with_the_rest() -> None:
    assert is_explosive_exception("1.4s")
    assert not must_segregate("1.4S", "1.4S")


def test_one_four_s_is_still_kept_from_other_explosives() -> None:
    assert must_segregate("1.4S", "1.4G")


def test_the_conflicting_pairs_come_back_from_a_set_of_classes() -> None:
    assert conflicts(["3", "5.1", "9"]) == (("3", "5.1"),)


def test_a_set_with_nothing_conflicting_comes_back_empty() -> None:
    assert conflicts(["3", "9", "2.2"]) == ()


def test_a_set_with_two_conflicts_reports_both() -> None:
    assert conflicts(["3", "5.1", "5.2"]) == (("3", "5.1"), ("3", "5.2"))


def test_no_radioactivity_needs_no_separation() -> None:
    assert separation_for(Decimal("0")) == Decimal("0.0")


def test_the_separation_grows_with_the_transport_index() -> None:
    assert separation_for(Decimal("0.4")) == Decimal("0.3")
    assert separation_for(Decimal("1.0")) == Decimal("0.5")
    assert separation_for(Decimal("3.9")) == Decimal("1.0")


def test_a_negative_transport_index_is_refused() -> None:
    with pytest.raises(DataError, match="cannot be negative"):
        separation_for(Decimal("-1"))


def test_an_index_past_the_table_is_refused() -> None:
    with pytest.raises(DataError, match="past the top of the separation table"):
        separation_for(Decimal("60"))
