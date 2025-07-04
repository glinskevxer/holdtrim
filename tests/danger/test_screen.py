from decimal import Decimal

from holdtrim.danger import screen
from holdtrim.danger.screen import Placement
from holdtrim.model.danger import DangerousGoods
from tests.fleet.test_type_store import a_type

NO_PACKING_GROUP = ("1.", "2.", "7")


def entry(hazard: str = "3", **changes: object) -> DangerousGoods:
    group = "" if hazard.startswith(NO_PACKING_GROUP) else "II"
    fields: dict[str, object] = {
        "un_number": 1263,
        "proper_shipping_name": "Paint",
        "hazard_class": hazard,
        "packages": 4,
        "net_quantity": Decimal("5.000"),
        "unit": "L",
        "packing_group": group,
    }
    fields.update(changes)
    return DangerousGoods(**fields)  # type: ignore[arg-type]


def placed(
    position: str,
    hazard: str = "3",
    awb: str = "125-12345675",
    entries: tuple[DangerousGoods, ...] | None = None,
    *,
    in_device: bool = True,
) -> Placement:
    return Placement(
        position=position,
        awb=awb,
        entries=entries if entries is not None else (entry(hazard),),
        in_device=in_device,
    )


def test_a_placement_lists_its_classes_and_risks() -> None:
    held = Placement(
        position="11P", awb="125-12345675", entries=(entry("3", subsidiary_risks=("8",)),)
    )
    assert held.classes == ("3", "8")


def test_a_freighter_takes_cargo_only_shipments() -> None:
    held = (placed("11P", entries=(entry("3", cargo_aircraft_only=True),)),)
    assert screen.on_this_aeroplane(held, freighter=True) == ()


def test_a_passenger_flight_refuses_a_cargo_only_shipment() -> None:
    held = (placed("11P", entries=(entry("3", cargo_aircraft_only=True),)),)
    found = screen.on_this_aeroplane(held, freighter=False)
    assert found[0].check == "cargo aircraft only"
    assert "may only fly on a freighter" in found[0].detail


def test_two_classes_that_segregate_may_not_share_a_position() -> None:
    held = (placed("11P", "3"), placed("11P", "5.1", awb="125-20000048"))
    found = screen.within_positions(held)
    assert found[0].check == "segregation"
    assert "oxidiser" in found[0].detail


def test_two_classes_that_travel_together_share_a_position() -> None:
    held = (placed("11P", "3"), placed("11P", "9", awb="125-20000048"))
    assert screen.within_positions(held) == ()


def test_loose_conflicting_classes_in_neighbouring_positions_are_found() -> None:
    held = (
        placed("11P", "3", in_device=False),
        placed("21P", "5.1", awb="125-20000048", in_device=False),
    )
    found = screen.between_positions(held, a_type().layout)
    assert found[0].check == "separation"


def test_the_same_classes_in_devices_are_not_a_separation_problem() -> None:
    held = (placed("11P", "3"), placed("21P", "5.1", awb="125-20000048"))
    assert screen.between_positions(held, a_type().layout) == ()


def test_positions_that_are_not_neighbours_are_fine_loose() -> None:
    held = (
        placed("11P", "3", in_device=False),
        placed("51", "5.1", awb="125-20000048", in_device=False),
    )
    assert screen.between_positions(held, a_type().layout) == ()


def test_a_small_transport_index_is_a_note_and_not_a_refusal() -> None:
    held = (
        placed(
            "11P",
            "7",
            entries=(entry("7", transport_index=Decimal("0.4"), unit="TBq", packages=1),),
        ),
    )
    found = screen.radioactivity(held)
    assert found[0].severity == "watch"
    assert "0.3 m of separation" in found[0].detail


def test_too_much_radioactivity_in_one_position_is_a_refusal() -> None:
    held = (
        placed(
            "11P",
            "7",
            entries=(entry("7", transport_index=Decimal("30"), unit="TBq", packages=4),),
        ),
    )
    found = screen.radioactivity(held)
    assert found[0].severity == "stop"
    assert "allowed in one position" in found[0].detail


def test_no_radioactivity_is_reported_at_all() -> None:
    assert screen.radioactivity((placed("11P", "3"),)) == ()


def test_an_explosive_sharing_its_position_is_found() -> None:
    held = (
        placed("11P", "1.4G", entries=(entry("1.4G", packing_group=""),)),
        placed("11P", "3", awb="125-20000048"),
    )
    found = screen.explosives(held)
    assert found[0].check == "explosive"


def test_one_four_s_may_share_a_position() -> None:
    held = (
        placed("11P", "1.4S", entries=(entry("1.4S", packing_group=""),)),
        placed("11P", "3", awb="125-20000048"),
    )
    assert screen.explosives(held) == ()


def test_an_explosive_on_its_own_is_fine() -> None:
    held = (placed("11P", "1.4G", entries=(entry("1.4G", packing_group=""),)),)
    assert screen.explosives(held) == ()


def test_the_whole_screen_runs_every_check() -> None:
    held = (placed("11P", "3"), placed("11P", "5.1", awb="125-20000048"))
    found = screen.screen(held, a_type().layout, freighter=True)
    assert [finding.check for finding in found] == ["segregation"]
    assert not screen.acceptable(found)


def test_a_clean_load_screens_acceptable() -> None:
    found = screen.screen((placed("11P", "3"),), a_type().layout)
    assert found == ()
    assert screen.acceptable(found)
