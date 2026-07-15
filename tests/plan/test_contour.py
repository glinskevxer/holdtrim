from holdtrim.model.hold import HoldLayout
from holdtrim.plan.contour import check, fits, tapered, wasted
from tests.fleet.test_type_store import a_type, position


def deck() -> HoldLayout:
    return HoldLayout(
        positions=(
            position("11P", "9.400"),
            position("21P", "12.600"),
            position("31P", "15.800"),
            position("51", "18.100", accepts=(), compartment="BULK"),
        )
    )


def test_the_ends_of_a_compartment_taper() -> None:
    assert tapered(deck()) == frozenset({"11P", "31P"})


def test_a_compartment_with_too_few_positions_does_not_taper() -> None:
    assert "51" not in tapered(deck())


def test_the_fixture_type_has_no_tapered_positions() -> None:
    assert tapered(a_type().layout) == frozenset()


def test_a_flat_device_does_not_fit_where_it_tapers() -> None:
    assert not fits(deck(), "11P", "flat")
    assert fits(deck(), "21P", "flat")


def test_a_sloping_device_fits_anywhere() -> None:
    assert fits(deck(), "11P", "sloping")
    assert fits(deck(), "21P", "sloping")


def test_a_sloping_device_in_a_square_position_wastes_space() -> None:
    assert wasted(deck(), "21P", "sloping")
    assert not wasted(deck(), "11P", "sloping")


def test_a_flat_device_never_wastes_anything() -> None:
    assert not wasted(deck(), "21P", "flat")


def test_a_flat_device_where_it_tapers_is_a_note() -> None:
    found = check(deck(), {"11P": "flat"})
    assert found[0].check == "contour"
    assert found[0].severity == "watch"
    assert "under the roof" in found[0].detail


def test_a_sloping_device_in_a_square_position_is_a_note() -> None:
    found = check(deck(), {"21P": "sloping"})
    assert "wastes the space" in found[0].detail


def test_a_load_that_is_the_right_shape_reports_nothing() -> None:
    assert check(deck(), {"11P": "sloping", "21P": "flat"}) == ()


def test_every_position_is_checked() -> None:
    found = check(deck(), {"11P": "flat", "21P": "sloping"})
    assert len(found) == 2
    assert [finding.where for finding in found] == ["11P", "21P"]
