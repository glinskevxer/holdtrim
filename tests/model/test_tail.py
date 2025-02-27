from datetime import date
from decimal import Decimal

import pytest

from holdtrim.errors import DataError, IdentifierError
from holdtrim.model.tail import Tail, add_months


def tail(**changes: object) -> Tail:
    fields: dict[str, object] = {
        "registration": "OY-JAF",
        "type_code": "AT7F",
        "dry_operating_weight": 13640,
        "dry_operating_index": Decimal("46.2"),
        "weighed_on": date(2024, 6, 18),
        "serial_number": "0412",
    }
    fields.update(changes)
    return Tail(**fields)  # type: ignore[arg-type]


def test_months_add_on_to_a_date() -> None:
    assert add_months(date(2024, 6, 18), 60) == date(2029, 6, 18)
    assert add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)


def test_months_add_across_a_leap_year_end() -> None:
    assert add_months(date(2023, 2, 28), 12) == date(2024, 2, 28)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_a_tail_normalises_its_registration_and_type() -> None:
    assert tail(registration="oy-jaf", type_code="at7f").registration == "OY-JAF"
    assert tail(type_code=" at7f ").type_code == "AT7F"


def test_a_registration_that_is_not_one_is_refused() -> None:
    with pytest.raises(IdentifierError, match="not an aircraft registration"):
        tail(registration="the blue one")


def test_a_tail_with_no_type_is_refused() -> None:
    with pytest.raises(DataError, match="not tied to a type"):
        tail(type_code="   ")


def test_a_tail_with_no_dry_operating_weight_is_refused() -> None:
    with pytest.raises(DataError, match="no dry operating weight"):
        tail(dry_operating_weight=0)


def test_an_unknown_status_is_refused() -> None:
    with pytest.raises(DataError, match="no status this build knows"):
        tail(status="parked up somewhere")


def test_a_weighing_valid_for_no_time_is_refused() -> None:
    with pytest.raises(DataError, match="valid for no time"):
        tail(weighing_valid_months=0)


def test_the_weighing_expires_five_years_after_it_was_done() -> None:
    assert tail().weighing_expires == date(2029, 6, 18)


def test_a_weighing_stands_up_to_the_day_it_expires() -> None:
    assert tail().weighing_current(date(2029, 6, 18))
    assert not tail().weighing_current(date(2029, 6, 19))


def test_the_days_left_run_negative_once_it_has_gone() -> None:
    assert tail().days_of_weighing_left(date(2029, 6, 8)) == 10
    assert tail().days_of_weighing_left(date(2029, 6, 28)) == -10


def test_only_an_in_service_tail_is_loadable() -> None:
    assert tail().loadable
    assert not tail(status="maintenance").loadable


def test_a_variation_moves_the_weight_and_the_index_together() -> None:
    changed = tail().with_variation(-120, Decimal("-0.8"))
    assert changed.dry_operating_weight == 13520
    assert changed.dry_operating_index == Decimal("45.4")


def test_a_variation_leaves_the_weighing_and_the_status_alone() -> None:
    changed = tail(status="stored").with_variation(80, Decimal("0.4"))
    assert changed.weighed_on == date(2024, 6, 18)
    assert changed.status == "stored"
    assert changed.serial_number == "0412"


def test_a_tail_describes_itself_in_one_line() -> None:
    assert tail().describe() == "OY-JAF AT7F DOW 13640 kg DOI 46.2 (in service)"
