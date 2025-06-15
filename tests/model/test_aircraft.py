from decimal import Decimal

import pytest

from holdtrim.balance.fuel import FuelPoint, FuelTable
from holdtrim.errors import DataError, NotFoundError
from holdtrim.model.aircraft import AircraftType, MacGeometry, StructuralLimits
from holdtrim.model.envelope import Envelope, EnvelopePoint
from holdtrim.model.hold import HoldLayout
from holdtrim.model.position import Position


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


def layout() -> HoldLayout:
    return HoldLayout(
        positions=(
            Position(
                code="11P",
                compartment="MAIN",
                arm=Decimal("9.400"),
                max_weight=3175,
                length=Decimal("3.175"),
                width=Decimal("2.235"),
                max_running_load=1200,
                max_area_load=732,
                accepts=("PMC",),
            ),
            Position(
                code="21P",
                compartment="MAIN",
                arm=Decimal("12.600"),
                max_weight=3175,
                length=Decimal("3.175"),
                width=Decimal("2.235"),
                max_running_load=1200,
                max_area_load=732,
                accepts=("PMC",),
            ),
        )
    )


def envelopes() -> tuple[Envelope, ...]:
    shape = (
        EnvelopePoint(weight=13000, forward_index=Decimal("38"), aft_index=Decimal("62")),
        EnvelopePoint(weight=20800, forward_index=Decimal("46"), aft_index=Decimal("57")),
    )
    return (
        Envelope(name="zero fuel", points=shape),
        Envelope(name="takeoff", points=shape),
        Envelope(name="landing", points=shape),
    )


def a_type(**changes: object) -> AircraftType:
    fields: dict[str, object] = {
        "code": "AT7F",
        "name": "ATR 72 freighter",
        "limits": limits(),
        "geometry": geometry(),
        "layout": layout(),
        "envelopes": envelopes(),
        "fuel": FuelTable(
            points=(
                FuelPoint(weight=0, index=Decimal("0.0")),
                FuelPoint(weight=4500, index=Decimal("1.2")),
            )
        ),
    }
    fields.update(changes)
    return AircraftType(**fields)  # type: ignore[arg-type]


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
    assert a_type(code="at7f").code == "AT7F"


def test_a_type_code_of_the_wrong_shape_is_refused() -> None:
    with pytest.raises(DataError, match="three to five letters"):
        a_type(code="AT")


def test_a_type_with_no_name_is_refused() -> None:
    with pytest.raises(DataError, match="has no name"):
        a_type(name="  ")


def test_structural_payload_is_zero_fuel_weight_less_the_empty_weight() -> None:
    assert a_type(empty_weight=13100).structural_payload == 7700


def test_a_type_heavier_empty_than_its_zero_fuel_weight_is_refused() -> None:
    with pytest.raises(DataError, match="weighs more empty"):
        a_type(empty_weight=21000)


def test_a_type_describes_itself_in_one_line() -> None:
    assert a_type().describe() == "AT7F ATR 72 freighter MZFW 20800 kg 2 positions"


def test_the_usable_fuel_is_the_end_of_the_fuel_table() -> None:
    assert a_type().usable_fuel == 4500


def test_the_three_envelopes_come_back_by_name() -> None:
    assert a_type().envelope("takeoff").name == "takeoff"
    assert a_type().envelope("ZERO FUEL").name == "zero fuel"


def test_asking_for_an_envelope_the_type_has_not_got() -> None:
    with pytest.raises(NotFoundError, match="no ferry envelope"):
        a_type().envelope("ferry")


def test_a_type_missing_the_landing_envelope_is_refused() -> None:
    with pytest.raises(DataError, match="has no landing envelope"):
        a_type(envelopes=envelopes()[:2])


def test_the_envelopes_come_back_in_name_order_however_they_went_in() -> None:
    shuffled = tuple(reversed(envelopes()))
    names = [shape.name for shape in a_type(envelopes=shuffled).envelopes]
    assert names == ["landing", "takeoff", "zero fuel"]


def test_a_type_carrying_the_same_envelope_twice_is_refused() -> None:
    with pytest.raises(DataError, match="same envelope twice"):
        a_type(envelopes=(*envelopes(), envelopes()[0]))


def test_the_floor_can_take_more_than_the_certificate_allows() -> None:
    assert a_type(empty_weight=14500).positions_hold_more_than_the_certificate


def test_a_light_type_with_a_small_layout_does_not_outrun_its_certificate() -> None:
    assert not a_type(empty_weight=13100).positions_hold_more_than_the_certificate
