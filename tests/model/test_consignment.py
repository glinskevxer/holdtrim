from datetime import date
from decimal import Decimal

import pytest

from holdtrim.errors import DataError
from holdtrim.ids import AirWaybill
from holdtrim.model.consignment import Consignment


def consignment(**changes: object) -> Consignment:
    fields: dict[str, object] = {
        "awb": AirWaybill(prefix="125", serial=1234567),
        "origin": "BLL",
        "destination": "LGG",
        "pieces": 8,
        "gross_weight": 1240,
        "volume": Decimal("4.200"),
        "commodity": "machine parts",
        "ready_on": date(2025, 5, 12),
    }
    fields.update(changes)
    return Consignment(**fields)  # type: ignore[arg-type]


def test_the_route_reads_the_way_a_manifest_writes_it() -> None:
    assert consignment().route == "BLLLGG"


def test_a_consignment_going_nowhere_is_refused() -> None:
    with pytest.raises(DataError, match="to itself"):
        consignment(destination="BLL")


def test_a_consignment_with_no_pieces_is_refused() -> None:
    with pytest.raises(DataError, match="has no pieces"):
        consignment(pieces=0)


def test_a_consignment_with_no_weight_is_refused() -> None:
    with pytest.raises(DataError, match="has no weight"):
        consignment(gross_weight=0)


def test_a_consignment_with_no_commodity_is_refused() -> None:
    with pytest.raises(DataError, match="no commodity description"):
        consignment(commodity="   ")


def test_the_volumetric_weight_is_the_tariff_ratio() -> None:
    assert consignment(volume=Decimal("1.000")).volumetric_weight == 167


def test_a_dense_shipment_charges_on_its_gross_weight() -> None:
    dense = consignment(gross_weight=1240, volume=Decimal("1.000"))
    assert dense.chargeable_weight == 1240
    assert not dense.bulky


def test_a_light_bulky_shipment_charges_on_its_volume() -> None:
    light = consignment(gross_weight=400, volume=Decimal("6.000"))
    assert light.chargeable_weight == 1002
    assert light.bulky


def test_density_is_weight_over_volume() -> None:
    assert consignment(gross_weight=1240, volume=Decimal("4.000")).density == Decimal("310.0")


def test_density_with_no_volume_measured_is_zero() -> None:
    assert consignment(volume=Decimal("0")).density == Decimal("0.0")


def test_the_average_piece_rounds_up() -> None:
    assert consignment(pieces=8, gross_weight=1240).average_piece == 155
    assert consignment(pieces=3, gross_weight=100).average_piece == 34


def test_handling_codes_come_back_sorted_and_upper_case() -> None:
    assert consignment(handling=("eaw", "PER", "per")).handling == ("EAW", "PER")


def test_a_handling_code_of_the_wrong_shape_is_refused() -> None:
    with pytest.raises(DataError, match="not a handling code"):
        consignment(handling=("PERISHABLE",))


def test_a_consignment_answers_which_codes_it_carries() -> None:
    loaded = consignment(handling=("PER",))
    assert loaded.carries("per")
    assert not loaded.carries("AVI")


def test_a_consignment_describes_itself_for_a_manifest() -> None:
    line = consignment(handling=("PER",)).describe()
    assert line == "125-12345675 BLLLGG 8/1240 machine parts PER"


def test_a_consignment_with_no_codes_leaves_no_trailing_space() -> None:
    assert consignment().describe().endswith("machine parts")
