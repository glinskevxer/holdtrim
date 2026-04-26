from datetime import date
from decimal import Decimal

from holdtrim.cargo import acceptance
from holdtrim.ids import AirWaybill
from holdtrim.model.consignment import Consignment
from tests.fleet.test_type_store import a_type
from tests.sheet.test_loadsheet import sector


def consignment(**changes: object) -> Consignment:
    fields: dict[str, object] = {
        "awb": AirWaybill(prefix="125", serial=1234567),
        "origin": "BLL",
        "destination": "LGG",
        "pieces": 8,
        "gross_weight": 1240,
        "volume": Decimal("4.200"),
        "commodity": "machine parts",
        "ready_on": date(2025, 5, 11),
    }
    fields.update(changes)
    return Consignment(**fields)  # type: ignore[arg-type]


def test_a_shipment_on_the_sector_passes_the_route_check() -> None:
    assert acceptance.route(consignment(), sector()) == ()


def test_a_shipment_out_of_somewhere_else_is_stopped() -> None:
    found = acceptance.route(consignment(origin="CDG"), sector())
    assert found[0].check == "route"
    assert found[0].severity == "stop"


def test_a_shipment_to_somewhere_else_is_only_a_note() -> None:
    found = acceptance.route(consignment(destination="CDG"), sector())
    assert found[0].severity == "watch"


def test_a_shipment_ready_before_the_flight_passes() -> None:
    assert acceptance.ready(consignment(), sector()) == ()


def test_a_shipment_ready_after_the_flight_is_stopped() -> None:
    found = acceptance.ready(consignment(ready_on=date(2025, 5, 14)), sector())
    assert "2 day(s) after" in found[0].detail


def test_a_freighter_carries_a_cargo_only_shipment() -> None:
    assert acceptance.carriage(consignment(handling=("RXB",)), sector()) == ()


def test_a_passenger_flight_does_not() -> None:
    found = acceptance.carriage(consignment(handling=("RXB",)), sector(freighter=False))
    assert found[0].check == "cargo only"


def test_an_ordinary_piece_weight_passes() -> None:
    assert acceptance.pieces(consignment(), a_type()) == ()


def test_a_piece_heavier_than_any_position_is_stopped() -> None:
    found = acceptance.pieces(consignment(pieces=1, gross_weight=4000), a_type())
    assert found[0].check == "piece weight"
    assert found[0].over_by == 825


def test_known_handling_codes_pass() -> None:
    assert acceptance.codes(consignment(handling=("PER",))) == ()


def test_the_room_left_on_the_flight_is_checked() -> None:
    assert acceptance.room(consignment(), 2000) == ()
    found = acceptance.room(consignment(), 900)
    assert found[0].over_by == 340


def test_every_acceptance_check_runs_together() -> None:
    found = acceptance.check(consignment(), sector(), a_type())
    assert found == ()
    assert acceptance.acceptable(found)


def test_the_underload_is_only_checked_when_it_is_given() -> None:
    assert acceptance.check(consignment(), sector(), a_type(), underload=900)
    assert acceptance.check(consignment(), sector(), a_type()) == ()


def test_a_shipment_with_only_a_note_is_still_acceptable() -> None:
    found = acceptance.check(consignment(destination="CDG"), sector(), a_type())
    assert acceptance.acceptable(found)


def test_a_shipment_that_is_stopped_is_not_acceptable() -> None:
    found = acceptance.check(consignment(origin="CDG"), sector(), a_type())
    assert not acceptance.acceptable(found)
