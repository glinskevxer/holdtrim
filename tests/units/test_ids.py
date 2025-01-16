import pytest

from holdtrim.errors import IdentifierError
from holdtrim.ids import (
    AirWaybill,
    Flight,
    UldCode,
    check_digit,
    parse_awb,
    parse_flight,
    parse_registration,
    parse_station,
    parse_uld,
)


def test_the_check_digit_is_the_serial_modulo_seven() -> None:
    assert check_digit(1234567) == 1234567 % 7
    assert check_digit(0) == 0
    assert check_digit(7) == 0


def test_a_serial_longer_than_seven_digits_is_refused() -> None:
    with pytest.raises(IdentifierError, match="longer than seven"):
        check_digit(10_000_000)


def test_a_negative_serial_is_refused() -> None:
    with pytest.raises(IdentifierError, match="cannot be negative"):
        check_digit(-1)


def test_an_air_waybill_reads_with_or_without_the_dash() -> None:
    with_dash = parse_awb("125-12345675")
    without = parse_awb("12512345675")
    assert with_dash == without
    assert with_dash.prefix == "125"
    assert with_dash.serial == 1234567


def test_the_written_form_carries_the_dash_and_the_plain_form_does_not() -> None:
    awb = AirWaybill(prefix="125", serial=1234567)
    assert awb.formatted() == "125-12345675"
    assert awb.plain() == "12512345675"
    assert str(awb) == "125-12345675"


def test_a_wrong_check_digit_names_the_one_that_was_expected() -> None:
    with pytest.raises(IdentifierError, match="5 was expected not 4"):
        parse_awb("125-12345674")


def test_something_that_is_not_a_waybill_number_is_refused() -> None:
    with pytest.raises(IdentifierError, match="not an air waybill"):
        parse_awb("125-1234")


def test_a_prefix_that_is_not_three_digits_is_refused() -> None:
    with pytest.raises(IdentifierError, match="airline prefix"):
        AirWaybill(prefix="12", serial=1234567)


def test_a_uld_code_splits_into_type_serial_and_owner() -> None:
    uld = parse_uld("AKE12345XX")
    assert uld.type_code == "AKE"
    assert uld.serial == "12345"
    assert uld.owner == "XX"
    assert uld.formatted() == "AKE12345XX"


def test_a_four_digit_serial_is_a_uld_code_too() -> None:
    assert parse_uld("PMC1234QH").serial == "1234"


def test_the_leading_letter_says_what_the_uld_is() -> None:
    assert parse_uld("AKE12345XX").category == "certified container"
    assert parse_uld("PMC12345XX").category == "certified pallet"
    assert parse_uld("DPE12345XX").category == "non certified container"


def test_certified_and_pallet_read_off_the_leading_letter() -> None:
    container = parse_uld("AKE12345XX")
    pallet = parse_uld("PMC12345XX")
    loose = parse_uld("DPE12345XX")
    assert container.certified
    assert not container.is_pallet
    assert pallet.certified
    assert pallet.is_pallet
    assert not loose.certified


def test_an_unknown_category_letter_is_refused() -> None:
    with pytest.raises(IdentifierError, match="unknown ULD category"):
        UldCode(type_code="ZKE", serial="12345", owner="XX")


def test_something_that_is_not_a_uld_code_is_refused() -> None:
    with pytest.raises(IdentifierError, match="not a ULD code"):
        parse_uld("AKE-12345")


def test_a_flight_designator_pads_its_number_to_three() -> None:
    assert parse_flight("QH12").formatted() == "QH012"
    assert parse_flight("QH0412").formatted() == "QH412"


def test_a_flight_suffix_survives_the_round_trip() -> None:
    flight = parse_flight("QH412A")
    assert flight == Flight(carrier="QH", number=412, suffix="A")
    assert str(flight) == "QH412A"


def test_a_designator_that_is_only_digits_is_refused() -> None:
    with pytest.raises(IdentifierError, match="not a flight designator"):
        parse_flight("12412")


def test_a_carrier_code_may_carry_a_digit() -> None:
    assert parse_flight("5X100").carrier == "5X"
    assert parse_flight("W6412").carrier == "W6"


def test_the_three_letter_icao_form_reads_too() -> None:
    assert parse_flight("AAL412").carrier == "AAL"


def test_registrations_normalise_to_upper_case() -> None:
    assert parse_registration("oy-jaf") == "OY-JAF"
    assert parse_registration(" G-ABCD ") == "G-ABCD"


def test_something_that_is_not_a_registration_is_refused() -> None:
    with pytest.raises(IdentifierError, match="not an aircraft registration"):
        parse_registration("OY JAF FOUR")


def test_station_codes_are_three_letters() -> None:
    assert parse_station("bll") == "BLL"
    with pytest.raises(IdentifierError, match="three letter station"):
        parse_station("EKYT")
