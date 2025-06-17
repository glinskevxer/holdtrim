from datetime import date
from decimal import Decimal

import pytest

from holdtrim.balance.loading import Balance, LoadedPosition, load_positions
from holdtrim.errors import DataError, NotFoundError
from holdtrim.model.tail import Tail
from tests.fleet.test_type_store import a_type


def tail() -> Tail:
    return Tail(
        registration="OY-JAF",
        type_code="AT7F",
        dry_operating_weight=13640,
        dry_operating_index=Decimal("46.2"),
        weighed_on=date(2024, 6, 18),
    )


def balance(weights: dict[str, int] | None = None, **changes: object) -> Balance:
    kind = a_type()
    fields: dict[str, object] = {
        "kind": kind,
        "tail": tail(),
        "loads": load_positions(kind, weights if weights is not None else {"11P": 2000}),
        "taxi_fuel": 90,
        "trip_fuel": 1450,
        "takeoff_fuel": 2600,
    }
    fields.update(changes)
    return Balance(**fields)  # type: ignore[arg-type]


def test_a_negative_load_is_refused() -> None:
    with pytest.raises(DataError, match="negative weight"):
        LoadedPosition(position=a_type().layout.position("11P"), weight=-1)


def test_a_load_describes_itself() -> None:
    load = LoadedPosition(position=a_type().layout.position("11P"), weight=2000, label="PMC12345QH")
    assert load.describe() == "11P PMC12345QH 2000 kg"


def test_a_load_with_no_label_reads_as_bulk() -> None:
    assert (
        LoadedPosition(position=a_type().layout.position("51"), weight=300)
        .describe()
        .endswith("bulk 300 kg")
    )


def test_the_payload_is_everything_loaded() -> None:
    assert balance({"11P": 2000, "21P": 1500}).payload == 3500


def test_an_empty_aeroplane_has_no_payload() -> None:
    assert balance({}).payload == 0


def test_the_zero_fuel_weight_is_the_dry_weight_plus_the_payload() -> None:
    assert balance({"11P": 2000}).zero_fuel.weight == 15640


def test_a_load_forward_of_the_reference_pulls_the_index_down() -> None:
    forward = balance({"11P": 2000}).zero_fuel.index
    assert forward < Decimal("46.2")


def test_a_load_aft_of_the_reference_pushes_the_index_up() -> None:
    assert balance({"51": 2000}).zero_fuel.index > Decimal("46.2")


def test_the_takeoff_weight_adds_the_fuel_in_the_tanks() -> None:
    assert balance().takeoff.weight == 18240


def test_the_landing_weight_takes_the_trip_fuel_off() -> None:
    assert balance().landing.weight == 16790


def test_the_ramp_weight_carries_the_taxi_fuel_too() -> None:
    assert balance().ramp_weight == 18330


def test_the_fuel_moves_the_index_off_the_fuel_table() -> None:
    figures = balance()
    correction = a_type().fuel.index_at(2600)
    assert figures.takeoff.index == figures.zero_fuel.index + correction


def test_the_landing_index_uses_the_fuel_that_is_left() -> None:
    figures = balance()
    correction = a_type().fuel.index_at(1150)
    assert figures.landing.index == figures.zero_fuel.index + correction


def test_the_three_conditions_come_back_in_order() -> None:
    assert [c.name for c in balance().conditions] == ["zero fuel", "takeoff", "landing"]


def test_a_condition_comes_back_by_name() -> None:
    assert balance().condition("TAKEOFF").weight == 18240


def test_a_condition_that_is_not_one_of_the_three_is_refused() -> None:
    with pytest.raises(DataError, match="not one of the three weights"):
        balance().condition("cruise")


def test_a_condition_reads_its_percent_mac() -> None:
    figures = balance({"11P": 2000})
    assert figures.zero_fuel.percent_mac(a_type()) < Decimal("52.0")


def test_the_loaded_positions_come_back_as_a_mapping() -> None:
    assert balance({"11P": 2000, "21P": 1500}).loaded_positions == {"11P": 2000, "21P": 1500}


def test_two_loads_in_one_position_add_up() -> None:
    kind = a_type()
    loads = (
        LoadedPosition(position=kind.layout.position("11P"), weight=800),
        LoadedPosition(position=kind.layout.position("11P"), weight=400),
    )
    assert balance(loads=loads).loaded_positions == {"11P": 1200}


def test_the_underload_is_the_smallest_of_the_three_margins() -> None:
    figures = balance({"11P": 2000})
    assert figures.underload == min(
        figures.underload_to_zero_fuel,
        figures.underload_to_takeoff,
        figures.underload_to_landing,
    )


def test_the_limiting_weight_is_named() -> None:
    assert balance({"11P": 2000}).limiting_weight in {"zero fuel", "takeoff", "landing"}


def test_a_heavy_load_on_short_fuel_makes_zero_fuel_the_limit() -> None:
    figures = balance({"11P": 3000, "21P": 3000}, takeoff_fuel=1600)
    assert figures.limiting_weight == "zero fuel"


def test_the_same_load_on_full_tanks_makes_takeoff_the_limit() -> None:
    figures = balance({"11P": 3000, "21P": 3000}, takeoff_fuel=4400)
    assert figures.limiting_weight == "takeoff"


def test_loading_a_position_that_is_not_on_the_type_is_refused() -> None:
    with pytest.raises(NotFoundError, match="no position 99X"):
        load_positions(a_type(), {"99X": 100})
