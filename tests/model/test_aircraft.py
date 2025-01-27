from decimal import Decimal

import pytest

from holdtrim.errors import DataError
from holdtrim.model.aircraft import AircraftType, MacGeometry, StructuralLimits


def limits() -> StructuralLimits:
    return StructuralLimits(
        max_ramp=23050, max_takeoff=22800, max_landing=22350, max_zero_fuel=20800
    )


def geometry() -> MacGeometry:
    return MacGeometry(
        reference_arm=Decimal("12.615"),
        lemac=Decimal("11.409"),
        mac_length=Decimal("2.303"),
        index_constant=Decimal("1000"),
        index_reference=Decimal("50"),
    )


def test_the_four_certificate_weights_come_back_by_name() -> None:
    assert limits().as_dict()["max_zero_fuel"] == 20800


def test_a_zero_weight_on_the_certificate_is_refused() -> None:
    with pytest.raises(DataError, match="max landing must be a positive weight"):
        StructuralLimits(max_ramp=23050, max_takeoff=22800, max_landing=0, max_zero_fuel=20800)


def test_ramp_weight_below_takeoff_weight_is_refused() -> None:
    with pytest.raises(DataError, match="max ramp weight cannot be below"):
        StructuralLimits(max_ramp=22000, max_takeoff=22800, max_landing=22350, max_zero_fuel=20800)


def test_takeoff_weight_below_landing_weight_is_refused() -> None:
    with pytest.raises(DataError, match="max takeoff weight cannot be below"):
        StructuralLimits(max_ramp=23050, max_takeoff=22000, max_landing=22350, max_zero_fuel=20800)


def test_landing_weight_below_zero_fuel_weight_is_refused() -> None:
    with pytest.raises(DataError, match="max landing weight cannot be below"):
        StructuralLimits(max_ramp=23050, max_takeoff=22800, max_landing=20000, max_zero_fuel=20800)


def test_the_taxi_allowance_is_the_gap_between_ramp_and_takeoff() -> None:
    assert limits().taxi_allowance == 250


def test_the_trailing_edge_is_a_chord_length_aft_of_the_leading_edge() -> None:
    assert geometry().trailing_edge == Decimal("13.712")


def test_an_arm_reads_as_a_percentage_of_chord() -> None:
    assert geometry().percent_of_mac(Decimal("11.409")) == Decimal("0.0")
    assert geometry().percent_of_mac(Decimal("13.712")) == Decimal("100.0")


def test_a_percentage_reads_back_as_an_arm() -> None:
    assert geometry().arm_at_percent(Decimal("0")) == Decimal("11.409")
    assert geometry().arm_at_percent(Decimal("50")) == Decimal("12.561")


def test_an_arm_forward_of_the_leading_edge_reads_negative() -> None:
    assert geometry().percent_of_mac(Decimal("11.000")) < 0


def test_a_chord_with_no_length_is_refused() -> None:
    with pytest.raises(DataError, match="must have a length"):
        MacGeometry(
            reference_arm=Decimal("12.615"),
            lemac=Decimal("11.409"),
            mac_length=Decimal("0"),
            index_constant=Decimal("1000"),
            index_reference=Decimal("50"),
        )


def test_an_index_constant_of_zero_is_refused() -> None:
    with pytest.raises(DataError, match="index constant must be positive"):
        MacGeometry(
            reference_arm=Decimal("12.615"),
            lemac=Decimal("11.409"),
            mac_length=Decimal("2.303"),
            index_constant=Decimal("0"),
            index_reference=Decimal("50"),
        )


def test_a_type_normalises_its_code() -> None:
    kind = AircraftType(code="at7f", name="ATR 72 freighter", limits=limits(), geometry=geometry())
    assert kind.code == "AT7F"


def test_a_type_code_of_the_wrong_shape_is_refused() -> None:
    with pytest.raises(DataError, match="three to five letters"):
        AircraftType(code="AT", name="ATR 72", limits=limits(), geometry=geometry())


def test_a_type_with_no_name_is_refused() -> None:
    with pytest.raises(DataError, match="has no name"):
        AircraftType(code="AT7F", name="  ", limits=limits(), geometry=geometry())


def test_structural_payload_is_zero_fuel_weight_less_the_empty_weight() -> None:
    kind = AircraftType(
        code="AT7F",
        name="ATR 72 freighter",
        limits=limits(),
        geometry=geometry(),
        empty_weight=13100,
    )
    assert kind.structural_payload == 7700


def test_a_type_heavier_empty_than_its_zero_fuel_weight_is_refused() -> None:
    with pytest.raises(DataError, match="weighs more empty"):
        AircraftType(
            code="AT7F",
            name="ATR 72 freighter",
            limits=limits(),
            geometry=geometry(),
            empty_weight=21000,
        )


def test_a_type_describes_itself_in_one_line() -> None:
    kind = AircraftType(code="AT7F", name="ATR 72 freighter", limits=limits(), geometry=geometry())
    assert kind.describe() == "AT7F ATR 72 freighter MZFW 20800 kg"
