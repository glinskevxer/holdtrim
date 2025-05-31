from datetime import date
from decimal import Decimal

import pytest

from holdtrim.cargo.buildup import BuildUp, build, put
from holdtrim.errors import RuleError, StateError
from holdtrim.ids import AirWaybill
from holdtrim.model.consignment import Consignment
from holdtrim.model.uld import Uld, uld


def device(**changes: object) -> Uld:
    fields: dict[str, object] = {
        "code": "PMC12345QH",
        "tare": 110,
        "max_gross": 4626,
        "at_station": "BLL",
    }
    fields.update(changes)
    return uld(**fields)  # type: ignore[arg-type]


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
    }
    fields.update(changes)
    return Consignment(**fields)  # type: ignore[arg-type]


def test_an_empty_device_still_weighs_its_tare() -> None:
    made = build(device())
    assert made.empty
    assert made.gross_weight == 110
    assert made.destination == ""


def test_the_gross_weight_is_tare_plus_everything_inside() -> None:
    made = build(device(), (consignment(1000006), consignment(2000004)))
    assert made.contents_weight == 2480
    assert made.gross_weight == 2590


def test_the_pieces_and_the_volume_add_up() -> None:
    made = build(device(), (consignment(1000006), consignment(2000004)))
    assert made.pieces == 16
    assert made.volume == Decimal("8.400")


def test_the_destination_comes_off_what_is_in_it() -> None:
    assert build(device(), (consignment(),)).destination == "LGG"


def test_a_device_that_is_not_serviceable_cannot_be_built() -> None:
    with pytest.raises(StateError, match="damaged and cannot be built up"):
        build(device(condition="damaged"))


def test_two_destinations_in_one_device_are_refused() -> None:
    made = build(device(), (consignment(1000006),))
    with pytest.raises(RuleError, match="is built for LGG"):
        put(made, consignment(2000004, destination="CDG"))


def test_the_same_waybill_twice_is_refused() -> None:
    made = build(device(), (consignment(),))
    with pytest.raises(RuleError, match="already in PMC12345QH"):
        put(made, consignment())


def test_going_over_the_maximum_gross_is_refused() -> None:
    made = build(device(), (consignment(1000006, gross_weight=4000),))
    with pytest.raises(RuleError, match="would be 74 kg over its maximum gross"):
        put(made, consignment(2000004, gross_weight=590))


def test_nothing_may_be_stacked_on_something_that_says_not_to() -> None:
    made = build(device(), (consignment(1000006, handling=("NST",)),))
    with pytest.raises(RuleError, match="nothing may be loaded on top"):
        put(made, consignment(2000004))


def test_something_unstackable_may_not_go_on_top_either() -> None:
    made = build(device(), (consignment(1000006),))
    with pytest.raises(RuleError, match="may not be stacked"):
        put(made, consignment(2000004, handling=("AVI",)))


def test_an_unstackable_consignment_on_its_own_is_fine() -> None:
    made = build(device(), (consignment(handling=("NST",)),))
    assert not made.stackable
    assert made.pieces == 8


def test_the_handling_codes_gather_from_everything_inside() -> None:
    made = build(
        device(),
        (consignment(1000006, handling=("PER",)), consignment(2000004, handling=("EAT", "PER"))),
    )
    assert made.handling_codes == ("EAT", "PER")


def test_a_device_with_dangerous_goods_says_so() -> None:
    made = build(device(), (consignment(handling=("RFL",)),))
    assert made.dangerous
    assert not build(device(), (consignment(),)).dangerous


def test_a_device_holding_a_cargo_only_shipment_says_so() -> None:
    assert build(device(), (consignment(handling=("RXB",)),)).cargo_aircraft_only


def test_a_device_answers_which_waybills_it_carries() -> None:
    made = build(device(), (consignment(),))
    assert made.carries("125-12345675")
    assert not made.carries("12520000048")


def test_a_build_up_describes_itself() -> None:
    made = build(device(), (consignment(handling=("PER",)),))
    assert made.describe() == "PMC12345QH LGG 8 pieces 1350 kg PER"


def test_an_empty_build_up_says_empty() -> None:
    assert build(device()).describe() == "PMC12345QH empty 0 pieces 110 kg"


def test_a_build_up_can_be_made_directly() -> None:
    made = BuildUp(uld=device(), consignments=(consignment(),))
    assert made.gross_weight == 1350
