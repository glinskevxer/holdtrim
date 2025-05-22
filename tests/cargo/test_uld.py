import pytest

from holdtrim.errors import DataError
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


def test_a_device_reads_its_base_off_its_code() -> None:
    assert device().base == "PMC"


def test_the_payload_capacity_is_the_gross_less_the_tare() -> None:
    assert device().payload_capacity == 4516


def test_a_device_with_no_tare_is_refused() -> None:
    with pytest.raises(DataError, match="no tare weight"):
        device(tare=0)


def test_a_device_that_cannot_hold_anything_is_refused() -> None:
    with pytest.raises(DataError, match="cannot hold anything"):
        device(tare=4626, max_gross=4626)


def test_an_unknown_condition_is_refused() -> None:
    with pytest.raises(DataError, match="no condition this build knows"):
        device(condition="bent a bit")


def test_an_unknown_contour_is_refused() -> None:
    with pytest.raises(DataError, match="no contour called"):
        device(contour="pointy")


def test_only_a_serviceable_device_is_loadable() -> None:
    assert device().loadable
    assert not device(condition="damaged").loadable


def test_a_device_with_no_station_is_in_transit() -> None:
    assert device(at_station="").in_transit
    assert not device().in_transit


def test_the_gross_weight_is_tare_plus_contents() -> None:
    assert device().gross_at(3000) == 3110


def test_a_negative_load_is_refused() -> None:
    with pytest.raises(DataError, match="negative weight"):
        device().gross_at(-1)


def test_a_load_inside_the_maximum_is_over_by_nothing() -> None:
    assert device().over_gross_by(4516) == 0


def test_a_load_past_the_maximum_reports_the_excess() -> None:
    assert device().over_gross_by(4600) == 84


def test_a_device_moves_station_and_keeps_everything_else() -> None:
    moved = device(condition="damaged").at("LGG")
    assert moved.at_station == "LGG"
    assert moved.condition == "damaged"
    assert moved.tare == 110


def test_a_device_describes_itself_for_a_stock_list() -> None:
    assert device().describe() == "PMC12345QH tare 110 max 4626 BLL serviceable"


def test_a_device_in_transit_says_so_in_its_line() -> None:
    assert "in transit" in device(at_station="").describe()
