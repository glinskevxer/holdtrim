import pytest

from holdtrim.errors import DataError, IdentifierError
from holdtrim.model.station import Station


def test_a_station_normalises_its_code_and_trims_its_name() -> None:
    station = Station(code="bll", name="  Billund  ", elevation_feet=247)
    assert station.code == "BLL"
    assert station.name == "Billund"


def test_a_station_with_no_name_is_refused() -> None:
    with pytest.raises(DataError, match="has no name"):
        Station(code="BLL", name="   ", elevation_feet=247)


def test_a_code_that_is_not_three_letters_is_refused() -> None:
    with pytest.raises(IdentifierError, match="three letter station"):
        Station(code="EKBI", name="Billund", elevation_feet=247)


def test_an_elevation_no_airfield_sits_at_is_refused() -> None:
    with pytest.raises(DataError, match="is not an airfield"):
        Station(code="BLL", name="Billund", elevation_feet=41000)


def test_a_field_below_sea_level_is_still_a_field() -> None:
    assert Station(code="TLV", name="Ben Gurion", elevation_feet=-1300).elevation_feet == -1300


def test_negative_free_storage_days_are_refused() -> None:
    with pytest.raises(DataError, match="negative free storage"):
        Station(code="BLL", name="Billund", elevation_feet=247, free_storage_days=-1)


def test_a_station_with_no_agent_is_self_handled() -> None:
    station = Station(code="BLL", name="Billund", elevation_feet=247)
    assert station.self_handled
    assert "self handled" in station.describe()


def test_an_agent_shows_in_the_listing_line() -> None:
    station = Station(
        code="LGG", name="Liege", elevation_feet=659, handling_agent="Swissport Cargo"
    )
    assert not station.self_handled
    assert station.describe() == "LGG Liege (Swissport Cargo)"


def test_stations_sort_by_code() -> None:
    bll = Station(code="BLL", name="Billund", elevation_feet=247)
    aar = Station(code="AAR", name="Aarhus", elevation_feet=82)
    assert sorted([bll, aar])[0] == aar
