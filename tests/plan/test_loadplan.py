import pytest

from holdtrim.errors import DataError, NotFoundError, RuleError
from holdtrim.plan.loadplan import Assignment, LoadPlan


def plan(*assignments: Assignment) -> LoadPlan:
    return LoadPlan(flight_key="QH412/2025-05-12", assignments=assignments)


def pallet(position: str = "11P", weight: int = 2000, uld: str = "PMC12345QH") -> Assignment:
    return Assignment(position=position, weight=weight, uld=uld, destination="LGG")


def test_an_assignment_with_no_position_is_refused() -> None:
    with pytest.raises(DataError, match="needs a position"):
        Assignment(position="  ", weight=100)


def test_an_assignment_with_no_weight_is_refused() -> None:
    with pytest.raises(DataError, match="nothing to hold"):
        Assignment(position="11P", weight=0)


def test_an_assignment_with_no_device_is_loose_cargo() -> None:
    loose = Assignment(position="51", weight=300)
    assert loose.loose
    assert loose.describe() == "51 bulk 300 kg"


def test_an_assignment_describes_its_device_and_destination() -> None:
    assert pallet().describe() == "11P PMC12345QH 2000 kg for LGG"


def test_a_plan_with_no_flight_is_refused() -> None:
    with pytest.raises(DataError, match="belong to a flight"):
        LoadPlan(flight_key="  ")


def test_a_position_assigned_twice_is_refused() -> None:
    with pytest.raises(DataError, match="assigned twice"):
        plan(pallet(), pallet(uld="PMC12346QH"))


def test_a_device_in_two_positions_is_refused() -> None:
    with pytest.raises(DataError, match="two positions"):
        plan(pallet(), pallet(position="21P"))


def test_an_edition_below_one_is_refused() -> None:
    with pytest.raises(DataError, match="starts at edition one"):
        LoadPlan(flight_key="QH412/2025-05-12", edition=0)


def test_an_empty_plan_carries_nothing() -> None:
    assert plan().empty
    assert plan().payload == 0


def test_the_payload_adds_up() -> None:
    assert plan(pallet(), pallet(position="21P", uld="PMC12346QH")).payload == 4000


def test_the_weights_come_back_keyed_by_position() -> None:
    assert plan(pallet()).weights == {"11P": 2000}


def test_the_devices_come_back_in_position_order() -> None:
    loaded = plan(pallet(), pallet(position="21P", uld="PMC12346QH"))
    assert loaded.devices == ("PMC12345QH", "PMC12346QH")


def test_loose_cargo_puts_no_device_in_the_list() -> None:
    assert plan(Assignment(position="51", weight=300)).devices == ()


def test_the_destinations_come_back_once_each() -> None:
    loaded = plan(pallet(), pallet(position="21P", uld="PMC12346QH"))
    assert loaded.destinations == ("LGG",)


def test_a_plan_answers_which_positions_it_holds() -> None:
    assert plan(pallet()).holds("11p")
    assert not plan(pallet()).holds("21P")


def test_what_is_in_a_position_comes_back() -> None:
    assert plan(pallet()).at("11P").uld == "PMC12345QH"


def test_asking_about_an_empty_position_is_refused() -> None:
    with pytest.raises(NotFoundError, match="nothing is planned for position 21P"):
        plan(pallet()).at("21P")


def test_a_device_is_found_by_its_code() -> None:
    assert plan(pallet()).carrying("pmc12345qh").position == "11P"


def test_a_device_that_is_not_in_the_plan_is_refused() -> None:
    with pytest.raises(NotFoundError, match="not in this plan"):
        plan(pallet()).carrying("PMC99999QH")


def test_assigning_adds_to_the_plan() -> None:
    loaded = plan().assign(pallet())
    assert loaded.positions == ("11P",)


def test_assigning_to_a_taken_position_is_refused() -> None:
    with pytest.raises(RuleError, match="already holds PMC12345QH"):
        plan(pallet()).assign(pallet(uld="PMC12346QH"))


def test_releasing_takes_it_back_out() -> None:
    assert plan(pallet()).release("11P").empty


def test_releasing_an_empty_position_is_refused() -> None:
    with pytest.raises(NotFoundError, match="nothing is planned"):
        plan(pallet()).release("21P")


def test_reissuing_moves_the_edition_on_and_keeps_the_load() -> None:
    reissued = plan(pallet()).reissued()
    assert reissued.edition == 2
    assert reissued.payload == 2000
