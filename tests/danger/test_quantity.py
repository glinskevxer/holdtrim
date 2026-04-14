from decimal import Decimal

from holdtrim.danger import quantity
from holdtrim.danger.quantity import Allowance, allowance_for, over_by, table
from tests.danger.test_screen import entry


def test_the_limit_depends_on_the_kind_of_flight() -> None:
    allowance = Allowance("3", "II", "L", Decimal("5"), Decimal("60"))
    assert allowance.limit(freighter=True) == Decimal("60")
    assert allowance.limit(freighter=False) == Decimal("5")


def test_an_allowance_describes_itself() -> None:
    line = Allowance("3", "II", "L", Decimal("5"), Decimal("60")).describe()
    assert "class 3 packing group II" in line
    assert "60 L on a freighter" in line


def test_a_listed_class_finds_its_allowance() -> None:
    allowance = allowance_for(entry("3"))
    assert allowance is not None
    assert allowance.packing_group == "II"


def test_a_class_with_no_packing_group_matches_the_blank_row() -> None:
    allowance = allowance_for(entry("9", packing_group=""))
    assert allowance is not None
    assert allowance.hazard_class == "9"


def test_a_class_nobody_listed_finds_nothing() -> None:
    assert allowance_for(entry("2.1", packing_group="")) is None


def test_a_package_inside_the_freighter_limit_is_over_by_nothing() -> None:
    assert over_by(entry("3", net_quantity=Decimal("5")), freighter=True) == Decimal("0")


def test_the_same_package_is_over_the_passenger_limit() -> None:
    assert over_by(entry("3", net_quantity=Decimal("30")), freighter=False) > 0


def test_an_unlisted_class_is_over_by_nothing() -> None:
    assert over_by(entry("2.1", packing_group=""), freighter=True) == Decimal("0")


def test_a_package_over_the_limit_stops_the_flight() -> None:
    found = quantity.check((entry("3", net_quantity=Decimal("90")),), freighter=True)
    assert found[0].check == "quantity"
    assert found[0].severity == "stop"
    assert "against a limit of 60 L" in found[0].detail


def test_a_package_inside_the_limit_is_not_reported() -> None:
    assert quantity.check((entry("3", net_quantity=Decimal("5")),), freighter=True) == ()


def test_an_unlisted_class_is_a_note_and_not_a_refusal() -> None:
    found = quantity.check((entry("2.1", packing_group=""),), freighter=True)
    assert found[0].check == "unlisted"
    assert found[0].severity == "watch"


def test_the_place_reaches_the_finding() -> None:
    found = quantity.check(
        (entry("3", net_quantity=Decimal("90")),), freighter=True, where="11P 125-1"
    )
    assert found[0].where == "11P 125-1"


def test_the_whole_table_prints() -> None:
    lines = table()
    assert len(lines) > 10
    assert all("class" in line for line in lines)
