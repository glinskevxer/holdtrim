import pytest

from holdtrim.cargo import handling
from holdtrim.errors import DataError


def test_a_known_code_reads_back_its_meaning() -> None:
    assert handling.meaning("per") == "perishable"
    assert handling.meaning("RXB") == "explosive, division 1.4B"


def test_an_unknown_code_is_refused_by_name() -> None:
    with pytest.raises(DataError, match="ZZZ is not a handling code"):
        handling.rule("zzz")


def test_known_answers_without_raising() -> None:
    assert handling.known("cao")
    assert not handling.known("ZZZ")


def test_the_unknown_codes_come_back_upper_case() -> None:
    assert handling.unknown(("per", "zzz", "qqq")) == ("ZZZ", "QQQ")


def test_a_list_of_known_codes_reports_nothing_unknown() -> None:
    assert handling.unknown(("PER", "EAT")) == ()


def test_the_dangerous_codes_are_picked_out_and_sorted() -> None:
    assert handling.dangerous(("PER", "rfl", "ICE")) == ("ICE", "RFL")


def test_ordinary_cargo_carries_no_dangerous_codes() -> None:
    assert handling.dangerous(("PER", "EAT")) == ()


def test_cargo_aircraft_only_comes_off_any_one_code() -> None:
    assert handling.cargo_aircraft_only(("PER", "RXB"))
    assert handling.cargo_aircraft_only(("CAO",))
    assert not handling.cargo_aircraft_only(("PER", "ICE"))


def test_one_unstackable_code_makes_the_whole_thing_unstackable() -> None:
    assert not handling.stackable(("EAT", "NST"))
    assert handling.stackable(("EAT", "PER"))


def test_live_animals_are_unstackable_without_saying_nst() -> None:
    assert not handling.stackable(("AVI",))


def test_dangerous_goods_and_live_animals_both_need_a_notice() -> None:
    assert handling.needs_notoc(("RFL",))
    assert handling.needs_notoc(("AVI",))
    assert not handling.needs_notoc(("EAT", "VAL"))


def test_the_cool_room_codes_are_picked_out() -> None:
    assert handling.temperature_controlled(("PER",))
    assert handling.temperature_controlled(("LHO",))
    assert not handling.temperature_controlled(("EAT",))


def test_every_code_in_the_table_is_three_letters() -> None:
    for code, entry in handling.CODES.items():
        assert len(code) == 3
        assert entry.code == code


def test_every_dangerous_code_needs_a_notice() -> None:
    for entry in handling.CODES.values():
        if entry.dangerous:
            assert entry.needs_notoc
