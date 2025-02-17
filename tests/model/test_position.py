from decimal import Decimal

import pytest

from holdtrim.errors import DataError
from holdtrim.model.position import Position


def pallet_position(**changes: object) -> Position:
    fields: dict[str, object] = {
        "code": "21P",
        "compartment": "MAIN",
        "arm": Decimal("14.200"),
        "max_weight": 3175,
        "length": Decimal("3.175"),
        "width": Decimal("2.235"),
        "max_running_load": 1200,
        "max_area_load": 732,
        "accepts": ("PMC", "PAG"),
    }
    fields.update(changes)
    return Position(**fields)  # type: ignore[arg-type]


def test_a_position_normalises_its_code_and_compartment() -> None:
    position = pallet_position(code=" 21p ", compartment="main")
    assert position.code == "21P"
    assert position.compartment == "MAIN"


def test_a_position_with_no_code_is_refused() -> None:
    with pytest.raises(DataError, match="needs a code"):
        pallet_position(code="  ")


def test_an_unknown_compartment_is_refused() -> None:
    with pytest.raises(DataError, match="no compartment this build knows"):
        pallet_position(compartment="TAIL")


def test_a_position_with_no_weight_limit_is_refused() -> None:
    with pytest.raises(DataError, match="no weight limit"):
        pallet_position(max_weight=0)


def test_a_position_with_no_floor_area_is_refused() -> None:
    with pytest.raises(DataError, match="no floor area"):
        pallet_position(width=Decimal("0"))


def test_a_position_with_no_running_load_limit_is_refused() -> None:
    with pytest.raises(DataError, match="no running load limit"):
        pallet_position(max_running_load=0)


def test_a_position_with_no_area_load_limit_is_refused() -> None:
    with pytest.raises(DataError, match="no area load limit"):
        pallet_position(max_area_load=0)


def test_the_bases_it_takes_come_back_sorted_and_upper_case() -> None:
    assert pallet_position(accepts=("pag", "pmc", "PMC")).accepts == ("PAG", "PMC")


def test_a_position_that_takes_no_uld_is_a_bulk_position() -> None:
    assert pallet_position(accepts=()).bulk


def test_a_position_answers_which_bases_it_takes() -> None:
    position = pallet_position()
    assert position.accepts_base("pmc")
    assert not position.accepts_base("AKE")


def test_the_floor_area_is_length_by_width() -> None:
    assert pallet_position().floor_area == Decimal("7.096")


def test_running_load_rounds_up_because_a_limit_is_a_limit() -> None:
    assert pallet_position().running_load(3175) == 1000
    assert pallet_position().running_load(3176) == 1001


def test_area_load_rounds_up_too() -> None:
    assert pallet_position().area_load(7096) == 1000


def test_a_weight_inside_the_limit_is_over_by_nothing() -> None:
    assert pallet_position().over_weight_by(3000) == 0


def test_a_weight_past_the_limit_reports_the_excess() -> None:
    assert pallet_position().over_weight_by(3400) == 225


def test_a_position_describes_itself_for_the_loading_instruction() -> None:
    assert pallet_position().describe() == "21P MAIN arm 14.200 max 3175 kg PAG/PMC"


def test_a_bulk_position_says_bulk_in_its_line() -> None:
    assert pallet_position(accepts=()).describe().endswith("bulk")
